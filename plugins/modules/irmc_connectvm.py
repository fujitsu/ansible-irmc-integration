#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_connectvm

short_description: connect iRMC Virtual Media Data

description:
    - Ansible module to connect iRMC Virtual Media Data via the iRMC RedFish interface.
    - Module Version V1.4.0.

requirements:
    - The module needs to run locally.
    - iRMC S6.
    - Python >= 3.14
    - Python modules 'requests', 'urllib3'

version_added: "2.4"

author:
    - Yutaka Kamioka (<yutaka.kamioka@fujitsu.com>)
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
    command:
        description: The virtual media connect command to be executed.
        required:    false
        default:     ConnectCD
        choices:     ['ConnectCD', 'ConnectHD', 'DisconnectCD', 'DisconnectHD']
'''

EXAMPLES = r'''
# Disconnect Virtual CD
- name: Disconnect Virtual CD
  fsas.primergy.irmc_connectvm:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "DisconnectCD"
  delegate_to: localhost
  tags:
    - disconnectCD

# Connect Virtual CD
- name: Connect Virtual CD
  fsas.primergy.irmc_connectvm:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "ConnectCD"
  delegate_to: localhost
  tags:
    - connectCD

# Disconnect Virtual HD
- name: Disconnect Virtual HD
  fsas.primergy.irmc_connectvm:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "DisconnectHD"
  delegate_to: localhost
  tags:
    - disconnectHD

# Connect Virtual HD
- name: Connect Virtual HD
  fsas.primergy.irmc_connectvm:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "ConnectHD"
  delegate_to: localhost
  tags:
    - connectHD
'''

RETURN = r'''
details:
    description:
        The default return value of Ansible (changed, failed, etc.) is returned.
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger


def irmc_connectvirtualmedia(module):
    result = dict(
        changed=False,
        status=0,
    )

    if module.check_mode:
        module.exit_json(msg='module was not run', **result)

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

    if irmc.vendor is None:
        result['msg'] = 'Failed to detect iRMC vendor. Vendor attribute not found in /redfish/v1'
        result['status'] = 20
        module.fail_json(**result)

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

    # Evaluate function params against iRMC
    if irmc.version and irmc.version.upper() == 'S4':
        vmaction_type = 'VirtualMediaAction'
    else:
        vmaction_type = f'{irmc.oem_prefix}VirtualMediaAction'

    vm_type = module.params['command'].replace('Connect', '').replace('Disconnect', '')
    vm_action = module.params['command'].replace(vm_type, '')
    vm_other_state = 'Connect' + vm_type if vm_action == 'Disconnect' else 'Disconnect' + vm_type

    allowedparams = dig(
        sysdata,
        'Actions', 'Oem', f'#{irmc.oem_prefix}ComputerSystem.VirtualMedia', f'{vmaction_type}@Redfish.AllowableValues',
    )

    if not allowedparams:
        module.fail_json(msg='VirtualMedia license may not be enabled.', status=20)

    if module.params['command'] not in allowedparams:
        if vm_other_state in allowedparams:
            result['skipped'] = True
            result['msg'] = f'iRMC virtual {vm_type} is already in state {module.params["command"]!r}'
            module.exit_json(**result)
        else:
            msg = f'Parameter {module.params["command"]} cannot be used at this time. Allowed: {allowedparams}'
            module.fail_json(warnings=msg, **result)

    # Get iRMC Virtual Media data
    vm_path = f'redfish/v1/Systems/0/Oem/{irmc.vendor}/VirtualMedia/'
    vmdata, _headers, status = irmc.get(vm_path)
    msg = 'OK' if status == 200 else f'Failed to get Virtual Media data from {vm_path}'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=vmdata)
    elif status != 200:
        module.fail_json(msg=msg, status=status)

    # Check Virtual Media Data
    remotemountenabled = dig(vmdata, 'RemoteMountEnabled')
    if not remotemountenabled:
        result['msg'] = 'Remote Mount of Virtual Media is not enabled!'
        result['status'] = 20
        module.fail_json(**result)

    # Set iRMC system data
    body = {vmaction_type: module.params['command']}
    action_path = f'redfish/v1/Systems/0/Actions/Oem/{irmc.oem_prefix}ComputerSystem.VirtualMedia'
    postdata, _headers, status = irmc.post(action_path, body)
    msg = 'OK' if status in (200, 202, 204) else f'Failed to execute Virtual Media action at {action_path}'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=postdata)
    elif status not in (200, 202, 204):
        module.fail_json(msg=msg, status=status)

    result['changed'] = True
    module.exit_json(**result)


def main():
    # import pdb; pdb.set_trace()
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(
            required=False,
            type='str',
            default='ConnectCD',
            choices=['ConnectCD','ConnectHD', 'DisconnectCD','DisconnectHD'],
        ),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_connectvirtualmedia(module)


if __name__ == '__main__':
    main()
