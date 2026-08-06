#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_getvm

short_description: get iRMC Virtual Media Data

description:
    - Ansible module to get iRMC Virtual Media Data via iRMC RedFish interface.
    - Module Version V1.4.0.

requirements:
    - The module needs to run locally.
    - iRMC S6.
    - Python >= 3.14
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
        description: The virtual media type whose data are to be read.
        required:    false
        default:     CDImage
        choices:     ['CDImage', 'HDImage']
'''

EXAMPLES = r'''
# Get Virtual CD data
- name: Get and show Virtual CD data
  tags:
    - getcd
  block:
    - name: Get Virtual CD data
      fsas.primergy.irmc_getvm:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        vm_type: CDImage
      register: cddata
      delegate_to: localhost
    - name: Show Virtual CD data
      ansible.builtin.debug:
        var: cddata.virtual_media_data

# Get Virtual HD data
- name: Get and show Virtual HD data
  tags:
    - gethd
  block:
    - name: Get Virtual HD data
      fsas.primergy.irmc_getvm:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        vm_type: HDImage
      register: hddata
      delegate_to: localhost
    - name: Show Virtual HD data
      ansible.builtin.debug:
        var: hddata.virtual_media_data
'''

RETURN = r'''
details:
    description:
        The following values are returned by requesting data for e.g. 'CDImage'.

    contains:
        CDImage:
            description: state of image
            returned: always
            type: string
            sample: Connected
        bootmode:
            description: boot source override mode for the next boot
            returned: always
            type: string
            sample: UEFI
        bootoverride:
            description: boot override type
            returned: always
            type: string
            sample: Once
        bootsource:
            description: boot device override for next boot
            returned: always
            type: string
            sample: BiosSetup
        image_name:
            description: name of the virtual image
            returned: always
            type: string
            sample: mybootimage.iso
        server:
            description: remote server where the image is located
            returned: always
            type: string
            sample: 192.168.2.1
        share_name:
            description: path on the remote server where the image is located
            returned: always
            type: string
            sample: isoimages
        share_type:
            description: share type (NFS or SMB)
            returned: always
            type: string
            sample: NFS
        usb_attach_mode:
            description: remote image attach mode
            returned: always
            type: string
            sample: AutoAttach
        user_domain:
            description: user domain for SMB share
            returned: always
            type: string
            sample: local.net
        user_name:
            description: user name for SM share
            returned: always
            type: string
            sample: test
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger


def irmc_getvirtualmedia(module):
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

    # M8 support: OEM Prefix Estimation
    if irmc.oem_prefix is None:
        result['msg'] = 'Failed to estimate iRMC OEM prefix. Vendor attribute not found in /redfish/v1'
        result['status'] = 20
        module.fail_json(**result)

    # Get iRMC system data
    sysdata, _headers, status = irmc.get('redfish/v1/Systems/0/')
    msg = 'OK' if status == 200 else 'Failed to get system data'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=sysdata)
    elif status != 200:
        module.fail_json(msg=msg, status=status)

    # Evaluate VM connection state
    vm_type_full = module.params['vm_type']
    vm_type = vm_type_full.replace('Image', '')
    allowedparams = dig(
        sysdata,
        'Actions',
        'Oem',
        f'#{irmc.oem_prefix}ComputerSystem.VirtualMedia',
        f'{irmc.oem_prefix}VirtualMediaAction@Redfish.AllowableValues',
    )

    # Determine current connection state
    vmdict = dict()
    if f'Connect{vm_type}' not in allowedparams:
        if f'Disconnect{vm_type}' not in allowedparams:
            vmdict[vm_type_full] = 'NotConfigured'
        else:
            vmdict[vm_type_full] = 'Connected'
    else:
        vmdict[vm_type_full] = 'Disconnected'

    # Get iRMC Virtual Media data
    vm_path = f'redfish/v1/Systems/0/Oem/{irmc.vendor}/VirtualMedia/'
    vmdata, _headers, status = irmc.get(vm_path)
    msg = 'OK' if status == 200 else f'Failed to get Virtual Media data from {vm_path}'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=vmdata)
    elif status != 200:
        module.fail_json(msg=msg, status=status)

    # Extract specified Virtual Media data
    remote_mount_enabled = dig(vmdata, 'RemoteMountEnabled')
    if not remote_mount_enabled:
        vmdict['remote_mount_disabled'] = 'Remote Mount of Virtual Media is not enabled!'
    vmdict['usb_attach_mode'] = dig(vmdata, 'UsbAttachMode')
    vmdict['bootsource'] = dig(sysdata, 'Boot', 'BootSourceOverrideTarget')
    vmdict['bootoverride'] = dig(sysdata, 'Boot', 'BootSourceOverrideEnabled')
    vmdict['bootmode'] = dig(sysdata, 'Boot', 'BootSourceOverrideMode')
    max_dev_no = dig(vmdata, vm_type_full, 'MaximumNumberOfDevices')
    if max_dev_no == 0:
        vmdict['no_vm_configured'] = f"No Virtual Media of Type '{vm_type_full}' is configured!"
    else:
        vmdict['image_name'] = dig(vmdata, vm_type_full, 'ImageName')
        vmdict['server'] = dig(vmdata, vm_type_full, 'Server')
        vmdict['share_name'] = dig(vmdata, vm_type_full, 'ShareName')
        vmdict['share_type'] = dig(vmdata, vm_type_full, 'ShareType')
        vmdict['user_domain'] = dig(vmdata, vm_type_full, 'UserDomain')
        vmdict['user_name'] = dig(vmdata, vm_type_full, 'UserName')
    result['virtual_media_data'] = vmdict
    module.exit_json(**result)


def main():
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        vm_type=dict(required=False, type='str', default='CDImage', choices=['CDImage', 'HDImage']),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_getvirtualmedia(module)


if __name__ == '__main__':
    main()
