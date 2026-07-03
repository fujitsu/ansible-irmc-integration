#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_powerstate

short_description: get or set server power state


description:
    - Ansible module to get or set server power state via iRMC RedFish interface.
    - Module Version V1.3.0

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
    command:
        description: Get or set server power state.
        required:    false
        default:     get
        choices:     ['get', 'set']
    state:
        description: Desired server power state for command 'set', ignored otherwise.
                     Options 'GracefulPowerOff' and ' GracefulReset' require
                     ServerView Agents running on server.
        required:    false
        choices:     ['PowerOn', 'PowerOff', 'PowerCycle', 'GracefulPowerOff', 'ImmediateReset', 'GracefulReset',
                      'PulseNmi', 'PressPowerButton']
'''

EXAMPLES = r'''
- name: Get and show server power state
  tags:
    - get
  block:
    - name: Get server power state
      fsas.primergy.irmc_powerstate:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
      register: result
      delegate_to: localhost
    - name: Show server power state
      ansible.builtin.debug:
        var: result.power_state

- name: Set server power state
  fsas.primergy.irmc_powerstate:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    state: "{{ state }}"
  delegate_to: localhost
  tags:
    - set
'''

RETURN = r'''
details:
    description: >
        If command is "get", the following values are returned.

        For other commands ("set"),
        the default return value of Ansible (changed, failed, etc.) is returned.

    contains:
        power_state:
            description: server power state
            returned: always
            type: string
            sample: "On"
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger


def irmc_powerstate(module: AnsibleModule) -> None:
    result = dict(
        changed=False,
        status=0,
    )

    if module.check_mode:
        result['msg'] = 'module was not run'
        module.exit_json(**result)

    # Preliminary parameter check
    if module.params['command'] == 'set' and module.params['state'] is None:
        result['msg'] = "Command 'set' requires 'state' parameter to be set!"
        result['status'] = 10
        module.fail_json(**result)

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

    power_state = dig(sysdata, 'PowerState')
    if module.params['command'] == 'get':
        result['power_state'] = power_state
        module.exit_json(**result)

    # Skip: current power state already matches requested state (ignoring 'Graceful' prefix)
    if f'Power{power_state}' == module.params['state'].replace('Graceful', ''):
        result['skipped'] = True
        result['msg'] = f"PRIMERGY server is already in state '{power_state}'"
        module.exit_json(**result)

    # Validate requested reset/power state against Redfish OEM allowable values
    allowedparams = dig(
        sysdata,
        'Actions',
        'Oem',
        f'#{irmc.oem_prefix}ComputerSystem.Reset',
        f'{irmc.oem_prefix}ResetType@Redfish.AllowableValues',
    )
    if module.params['state'] not in allowedparams:
        result['msg'] = f'{module.params["state"]!r} is not allowed now. Currently allowed: {allowedparams}'
        result['status'] = 11
        module.fail_json(**result)

    # Change iRMC power state
    body = {f'{irmc.oem_prefix}ResetType': module.params['state']}
    reset_path = f'redfish/v1/Systems/0/Actions/Oem/{irmc.oem_prefix}ComputerSystem.Reset'
    postdata, _headers, status = irmc.post(reset_path, body)
    msg = 'OK' if status in (200, 202, 204) else f'Failed to execute Power state change action at {reset_path}'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=postdata)
    elif status not in (200, 202, 204):
        module.fail_json(msg=msg, status=status)

    result['changed'] = True
    module.exit_json(**result)


def main() -> None:
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(required=False, type='str', default='get', choices=['get', 'set']),
        state=dict(required=False, type='str', choices=['PowerOn', 'PowerOff', 'PowerCycle', 'GracefulPowerOff',
                                                        'ImmediateReset', 'GracefulReset', 'PulseNmi',
                                                        'PressPowerButton']),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_powerstate(module)


if __name__ == '__main__':
    main()
