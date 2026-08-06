#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_eventlog

short_description: handle iRMC eventlogs

description:
    - Ansible module to handle iRMC eventlogs via Restful API.
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
    command:
        description: Handle iRMC eventlogs.
        required:    false
        default:     list
        choices:     ['list', 'get', 'clear']
    eventlog_type:
        description: Specific eventlog to handle.
        default:     SystemEventLog
        required:    false
        choices:     ['SystemEventLog', 'InternalEventLog']
    id:
        description: Specific eventlog ID to get.
        required:    false
'''

EXAMPLES = r'''
- name: List and show iRMC InternalEventLog
  tags:
    - list_internaleventlog
  block:
    - name: List iRMC InternalEventLog
      fsas.primergy.irmc_eventlog:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "list"
        eventlog_type: "InternalEventLog"
      delegate_to: localhost
      register: list_internaleventlog
    - name: Show list InternalEventLog
      ansible.builtin.debug:
        var: list_internaleventlog

# List iRMC SystemEventLog
- name: List and show iRMC SystemEventLog
  tags:
    - list_systemeventlog
  block:
    - name: List iRMC SystemEventLog
      fsas.primergy.irmc_eventlog:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "list"
        eventlog_type: "SystemEventLog"
      delegate_to: localhost
      register: list_systemeventlog
    - name: Show list SystemEventLog
      ansible.builtin.debug:
        var: list_systemeventlog

# Get specific InternalEventLog entry information
# Add '-e "id=xx"' to the command line argument of Playbook.
- name: Get and show a specific InternalEventLog entry
  tags:
    - get_internaleventlog
  block:
    - name: Get specific InternalEventLog entry information
      fsas.primergy.irmc_eventlog:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
        eventlog_type: "InternalEventLog"
        id: "{{ id | int }}"
      delegate_to: localhost
      register: get_internaleventlog
    - name: Show specific InternalEventLog
      ansible.builtin.debug:
        var: get_internaleventlog.eventlog_entry

# Get specific SystemEventLog entry information
# Add '-e "id=xx"' to the command line argument of Playbook.
- name: Get and show a specific SystemEventLog entry
  tags:
    - get_systemeventlog
  block:
    - name: Get specific SystemEventLog entry information
      fsas.primergy.irmc_eventlog:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
        eventlog_type: "SystemEventLog"
        id: "{{ id | int }}"
      delegate_to: localhost
      register: get_systemeventlog
    - name: Show get specific SystemEventLog
      ansible.builtin.debug:
        var: get_systemeventlog.eventlog_entry

# Clear iRMC InternalEventLog
- name: Clear iRMC InternalEventLog
  fsas.primergy.irmc_eventlog:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "clear"
    eventlog_type: "InternalEventLog"
  delegate_to: localhost
  tags:
    - clear_internaleventlog

# Clear iRMC SystemEventLog
- name: Clear iRMC SystemEventLog
  fsas.primergy.irmc_eventlog:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "clear"
    eventlog_type: "SystemEventLog"
  delegate_to: localhost
  tags:
    - clear_systemeventlog
'''

RETURN = r'''
details:
    description:
        If command is "get", the following values are returned.

        If command is "list", list of individual eventlog_entries is returned.

        For all other commands, the default return value of Ansible (changed, failed, etc.) is returned.

    contains:
        AlertGroup:
            description: group which caused the event
            returned: always
            type: string
            sample: Memory
        Cause:
            description: reason for the event if available
            returned: always
            type: string
            sample: The memory module was not approved and released for this system by the system manufacturer
        Created:
            description: dated of the event
            returned: always
            type: string
            sample: "2018-07-24T15:57:40+02:00"
        EventSource:
            description: where the event originated from
            returned: always
            type: string
            sample: iRMC S5
        Id:
            description: event ID
            returned: always
            type: int
            sample: 20
        Message:
            description: event entry text
            returned: always
            type: string
            sample: DIMM-1E Non Certified Memory Module detected - Warranty restricted!
        Resolutions:
            description: list of possible solitions for the problem, if available
            returned: always
            type: list
            sample:
        Severity:
            description: serverity of event
            returned: always
            type: string
            sample: Warning
        Type:
            description: event type
            returned: always
            type: string
            sample: SEL
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger


def irmc_eventlog(module):
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

    eventlog_type = module.params['eventlog_type']

    # Preliminary parameter check
    if module.params['command'] == 'get' and module.params['id'] is None:
        result['msg'] = "Command 'get' requires 'id' parameter to be set!"
        result['status'] = 10
        module.fail_json(**result)

    if module.params['command'] == 'list':
        logsdata, _headers, status = irmc.get(f'redfish/v1/Managers/iRMC/LogServices/{eventlog_type}/Entries')
        msg = 'OK' if status == 200 else 'Failed to get Log data'
        if status < 100:
            module.fail_json(msg=msg, status=status, exception=logsdata)
        elif status not in (200, 202, 204):
            module.fail_json(msg=msg, status=status)

        eventlogs = dig(logsdata, 'Members')
        result['eventlog'] = []
        for item in eventlogs:
            result['eventlog'].append(get_irmc_eventlog_info(module, irmc, item))

    elif module.params['command'] == 'clear':
        clear_log_path = f'redfish/v1/Managers/iRMC/LogServices/{eventlog_type}/Actions/LogService.ClearLog'
        clearlogdata, _headers, status = irmc.post(clear_log_path, '')
        msg = 'OK' if status == 200 else f'Failed to clear Log data at {clear_log_path}'
        if status < 100:
            module.fail_json(msg=msg, status=status, exception=clearlogdata)
        elif status not in (200, 202, 204):
            module.fail_json(msg=msg, status=status)
        result['changed'] = True

    # Get specific log
    else:
        get_log_path = f'redfish/v1/Managers/iRMC/LogServices/{eventlog_type}/Entries/{module.params["id"]}'
        logsdata, _headers, status = irmc.get(get_log_path)
        msg = 'OK' if status == 200 else f'Failed to get Log data at {get_log_path}'
        if status < 100:
            module.fail_json(msg=msg, status=status, exception=logsdata)
        elif status not in (200, 202, 204):
            module.fail_json(msg=msg, status=status)

        result['eventlog_entry'] = get_irmc_eventlog_info(module, irmc, logsdata)

    module.exit_json(**result)


def get_irmc_eventlog_info(module, irmc, item):
    eventlog = {}
    eventlog['Id'] = item['Id']
    eventlog['Severity'] = item['Severity']
    eventlog['Created'] = item['Created']
    eventlog['Type'] = item['EntryType']
    eventlog['AlertGroup'] = dig(item, 'Oem', irmc.vendor, 'AlertGroup')
    if module.params['eventlog_type'] == 'SystemEventLog':
        eventlog['EventSource'] = dig(item, 'Oem', irmc.vendor, 'EventSource')
        eventlog['Message'] = dig(item, 'Oem', irmc.vendor, 'MessageOEM', 'en')[0]
        if dig(item, 'Oem', irmc.vendor, 'Cause') is not None:
            eventlog['Cause'] = dig(item, 'Oem', irmc.vendor, 'Cause', 'en')[0]
        else:
            eventlog['Cause'] = None
        if dig(item, 'Oem', irmc.vendor, 'Resolutions') is not None:
            eventlog['Resolutions'] = dig(item, 'Oem', irmc.vendor, 'Resolutions', 'en')[0]
        else:
            eventlog['Resolutions'] = None
    else:
        eventlog['MessageId'] = item['MessageId']
        eventlog['Message'] = item['Message']
    return eventlog


def main():
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(required=False, type='str', default='list', choices=['list', 'get', 'clear']),
        eventlog_type=dict(
            required=False,
            type='str',
            default='SystemEventLog',
            choices=['SystemEventLog', 'InternalEventLog'],
        ),
        id=dict(required=False, type='int'),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_eventlog(module)


if __name__ == '__main__':
    main()
