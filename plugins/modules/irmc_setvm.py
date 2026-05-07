#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_setvm

short_description: set iRMC Virtual Media Data

description:
    - Ansible module to set iRMC Virtual Media Data via iRMC RedFish interface.
    - Module Version V1.4.0.

requirements:
    - The module needs to run locally.
    - iRMC S6.
    - Python >= 3.10
    - Python modules 'requests', 'urllib3'

version_added: "2.4"

author:
    - Tomohisa Nakai (<nakai.tomohisa@fujitsu.com>)
    - Nakamura Takayuki (@nakamura-taka)

options:
    irmc_url:
        description: IP address of the iRMC to be requested for data.
        required:    true
    irmc_username:
        description: iRMC user for basic authentication.
        required:    true
    irmc_password:
        description: Password for iRMC user for basic authentication.
        required:    true
    validate_certs:
        description: Evaluate SSL certificate (set to false for self-signed certificate).
        required:    false
        default:     true
    vm_type:
        description: The virtual media type to be set.
        required:    false
        default:     CDImage
        choices:     ['CDImage', 'HDImage']
    server:
        description: Remote server (IP or DNS name) where the image is located.
        required:    true
    share:
        description: Path on the remote server where the image is located.
        required:    true
    image:
        description: Name of the remote image.
        required:    true
    share_type:
        description: Share type (NFS, CIFS/SMB or HTTPS share).
        required:    false
        choices:     ['NFS', 'SMB', 'HTTPS']
    vm_domain:
        description: User domain in case of SMB share.
        required:    false
    vm_user:
        description: User account in case of SMB share.
        required:    false
    vm_password:
        description: User password in case of SMB share.
        required:    false
    force_remotemount_enabled:
        description: Forces iRMC to enable the remote mount feature.
        required:    false
    force_mediatype_active:
        description: Forces iRMC to activate one of the required remote media types.
        required:    false
'''

EXAMPLES = r'''
# Set Virtual CD
- name: Set Virtual CD
  fsas.primergy.irmc_setvm:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    share_type: "{{ share_type }}"
    server: "{{ server }}"
    share: "{{ share }}"
    image: "{{ image }}"
    vm_user: "{{ vm_user }}"
    vm_password: "{{ vm_password }}"
    vm_type: "CDImage"
  delegate_to: localhost
  tags:
    - setcd

# Set Virtual HD
- name: Set Virtual HD
  fsas.primergy.irmc_setvm:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    share_type: "{{ share_type }}"
    server: "{{ server }}"
    share: "{{ share }}"
    image: "{{ image }}"
    vm_user: "{{ vm_user }}"
    vm_password: "{{ vm_password }}"
    vm_type: "HDImage"
  delegate_to: localhost
  tags:
    - sethd
'''

RETURN = r'''
details:
    description:
        The default return value of Ansible (changed, failed, etc.) is returned.
'''


import json

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_scci_utils import setup_datadict
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger


def irmc_setvirtualmedia(module):
    result = dict(
        changed=False,
        status=0,
    )

    if module.check_mode:
        result['msg'] = 'module was not run'
        module.exit_json(**result)

    # Initialize logger
    logger = AnsibleLogger(module)

    # Initialize iRMC client
    irmc = iRMC(
        ipaddress=module.params['irmc_url'],
        username=module.params['irmc_username'],
        password=module.params['irmc_password'],
        validate_certs=module.params['validate_certs'],
        logger=logger,
    )

    # M8 support: Vendor detection
    if irmc.vendor is None:
        result['msg'] = 'Failed to detect iRMC vendor. Vendor attribute not found in /redfish/v1'
        result['status'] = 20
        module.fail_json(**result)

    vmparams, status = setup_datadict(module)

    # Get iRMC Virtual Media data
    vm_path = f'redfish/v1/Systems/0/Oem/{irmc.vendor}/VirtualMedia/'
    vmdata, _headers, status = irmc.get(vm_path)
    msg = 'OK' if status == 200 else f'Failed to get Virtual Media data from {vm_path}'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=vmdata)
    elif status != 200:
        module.fail_json(msg=msg, status=status)

    # Evaluate configured Virtual Media Data
    max_dev_no = dig(vmdata, module.params['vm_type'], 'MaximumNumberOfDevices')
    if max_dev_no == 0:
        if not module.params['force_mediatype_active']:
            result['warnings'] = "No Virtual Media of Type '" + module.params['vm_type'] + "' is configured!"
            result['status'] = 20
            module.fail_json(**result)
        else:
            new_max_dev_no = 1
    else:
        new_max_dev_no = max_dev_no

    remote_mount_enabled = dig(vmdata, 'RemoteMountEnabled')
    if not remote_mount_enabled and not module.params['force_remotemount_enabled']:
        result['msg'] = 'Remote Mount of Virtual Media is not enabled!'
        result['status'] = 30
        module.fail_json(**result)

    # Set iRMC system data
    body = setup_vmdata(vmparams, max_dev_no, new_max_dev_no)
    etag = dig(vmdata, '@odata.etag')
    headers = {'If-Match': str(etag)}
    patch, _headers, status = irmc.patch(vm_path, body, headers=headers)
    msg = 'OK' if status == 200 else f'Failed to update Virtual Media data at {vm_path}'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=patch)
    elif status != 200:
        module.fail_json(msg=msg, status=status)

    result['changed'] = True
    module.exit_json(**result)


def setup_vmdata(data, max_dev_no, new_max_dev_no):
    body = {
        data['vm_type']: {
            'Server': data['server'],
            'ShareName': data['share'],
            'ImageName': data['image'],
        },
    }
    if data['force_remotemount_enabled']:
        body['RemoteMountEnabled'] = True
    if max_dev_no == 0:
        body[data['vm_type']]['MaximumNumberOfDevices'] = new_max_dev_no
    if data['share_type'] is not None:
        body[data['vm_type']]['ShareType'] = data['share_type']
    if data['vm_domain'] is not None:
        body[data['vm_type']]['UserDomain'] = data['vm_domain']
    if data['vm_user'] is not None:
        body[data['vm_type']]['UserName'] = data['vm_user']
    if data['vm_password'] is not None:
        body[data['vm_type']]['Password'] = data['vm_password']
    return body


def main():
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        vm_type=dict(required=False, type='str', default='CDImage', choices=['CDImage', 'HDImage']),
        server=dict(required=True, type='str'),
        share=dict(required=True, type='str'),
        image=dict(required=True, type='str'),
        share_type=dict(required=False, type='str', choices=['NFS', 'SMB', 'HTTPS']),
        vm_domain=dict(required=False, type='str'),
        vm_user=dict(required=False, type='str'),
        vm_password=dict(required=False, type='str', no_log=True),
        force_remotemount_enabled=dict(required=False, type='bool', default=False),
        force_mediatype_active=dict(required=False, type='bool', default=False),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_setvirtualmedia(module)


if __name__ == '__main__':
    main()
