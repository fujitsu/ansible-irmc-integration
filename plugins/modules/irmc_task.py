#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_task

short_description: handle iRMC tasks

description:
    - Ansible module to handle iRMC tasks via Restful API.
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
    command:
        description: Handle iRMC tasks.
        required:    false
        default:     list
        choices:     ['list', 'get']
    id:
        description: Specific task to get.
        required:    false
'''

EXAMPLES = r'''
# List iRMC tasks
- block:
  - name: List iRMC tasks
    fsas.primergy.irmc_task:
      irmc_url: "{{ inventory_hostname }}"
      irmc_username: "{{ irmc_user }}"
      irmc_password: "{{ irmc_password }}"
      validate_certs: "{{ validate_certificate }}"
      command: "list"
    register: list
    delegate_to: localhost
  - name: Show list of tasks
    debug:
      var: list.tasks
  tags:
    - list

# Get specific task information
- block:
  - name: Get specific task information
    fsas.primergy.irmc_task:
      irmc_url: "{{ inventory_hostname }}"
      irmc_username: "{{ irmc_user }}"
      irmc_password: "{{ irmc_password }}"
      validate_certs: "{{ validate_certificate }}"
      command: "get"
      id: "{{ id | int }}"
    register: get
    delegate_to: localhost
  - name: Show specific task
    debug:
      var: get.task
  tags:
    - get
'''

RETURN = r'''
details:
    description:
        If command is "get", the following values are returned.

        If command is "list", list of individual task entries is returned.

    contains:
        Id:
            description: task ID
            returned: always
            type: int
            sample: 3
        Name:
            description: task name
            returned: always
            type: string
            sample: ProfileParametersApply
        StartTime:
            description: start time
            returned: always
            type: string
            sample: "2018-07-31 12:23:02"
        EndTime:
            description: end time
            returned: always
            type: string
            sample: "2018-07-31 12:26:44"
        State:
            description: task state
            returned: always
            type: string
            sample: Completed
        StateOem:
            description: Oem task state
            returned: always
            type: string
            sample: LcmSessFinished
        StateProgressPercent:
            description: state progress in %
            returned: always
            type: string
            sample: 100
        TotalProgressPercent:
            description: overall progress in %
            returned: always
            type: string
            sample: 100
'''

from pathlib import PurePosixPath

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger


def irmc_task(module):
    result = dict(
        changed=False,
        status=0,
    )

    if module.check_mode:
        result['msg'] = 'module was not run'
        module.exit_json(**result)

    # parameter check
    if module.params['command'] == 'get' and module.params['id'] is None:
        result['msg'] = "Command 'get' requires 'id' parameter to be set!"
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

    # M8 support: Vendor detection (required)
    if irmc.vendor is None:
        result['msg'] = 'Failed to detect iRMC vendor. Vendor attribute not found in /redfish/v1'
        result['status'] = 20
        module.fail_json(**result)

    if module.params['command'] == 'get':
        result['task'] = get_irmc_task_info(
            module,
            irmc,
            f'redfish/v1/TaskService/Tasks/{module.params["id"]}',
            module.params['id'],
        )

    if module.params['command'] == 'list':
        tasksdata, _headers, status = irmc.get('redfish/v1/TaskService/Tasks')
        msg = 'OK' if status == 200 else 'Failed to get tasks data'

        if status < 100:
            module.fail_json(msg=msg, status=status, exception=tasksdata)
        elif status not in (200, 202, 204):
            module.fail_json(msg=msg, status=status)
        tasks = dig(tasksdata, 'Members')

        result['tasks'] = []
        for task in tasks:
            task_url = dig(task, '@odata.id')
            task_id = PurePosixPath(task_url).name
            task_info = get_irmc_task_info(module, irmc, task_url, task_id)
            result['tasks'].append(task_info)

    module.exit_json(**result)


def get_irmc_task_info(module, irmc, url, task_id):
    taskdata, _headers, status = irmc.get(url)
    msg = 'OK' if status == 200 else 'Failed to get task data'

    if status < 100:
        module.fail_json(msg=msg, status=status, exception=taskdata)
    elif status not in (200, 202, 204):
        module.fail_json(msg=msg, status=status)

    task = {}
    task['Id'] = task_id
    task['Name'] = dig(taskdata, 'Name')
    task['State'] = dig(taskdata, 'TaskState')
    task['StateOem'] = dig(taskdata, 'Oem', irmc.vendor, 'StatusOEM')
    task['StateProgressPercent'] = dig(taskdata, 'Oem', irmc.vendor, 'StateProgressPercent')
    task['TotalProgressPercent'] = dig(taskdata, 'Oem', irmc.vendor, 'TotalProgressPercent')
    task['StartTime'] = dig(taskdata, 'StartTime')
    task['EndTime'] = dig(taskdata, 'EndTime')
    return task


def main():
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(required=False, type='str', default='list', choices=['list', 'get']),
        id=dict(required=False, type='int'),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_task(module)


if __name__ == '__main__':
    main()
