#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_raid

short_description: handle iRMC RAID

description:
    - Ansible module to configure a PRIMERGY server's RAID via iRMC.
    - Using this module may force the server into several reboots.
    - Module Version V1.4.0.

requirements:
    - The module needs to run locally.
    - iRMC S6
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
        description: How to handle iRMC RAID.
        required:    false
        default:     get
        choices:     ['get', 'create', 'delete']
    adapter:
        description: The logical number of the adapter to create/delete RAID arrays on/from.
                     The logical number is the value at the end of the id (ex. "RAIDAdapter0")
                     obtained by command="get".
        required:    false
    array:
        description: The logical number of the RAID array to delete. Use -1 for all arrays. Ignored for 'create'.
        required:    false
    level:
        description: Raid level of array to be created. Ignored for 'delete'.
        required:    false
    name:
        description: Name of the array to be created. Ignored for 'delete'.
        required:    false
    wait_for_finish:
        description: Wait for raid session to finish.
        required:    false
        default:     true
'''

EXAMPLES = r'''
- name: Get and show RAID configuration
  tags:
    - get
  block:
    - name: Get RAID configuration
      fsas.primergy.irmc_raid:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
      register: raid
      delegate_to: localhost
    - name: Show RAID configuration
      ansible.builtin.debug:
        var: raid.configuration

- name: Create RAID array
  fsas.primergy.irmc_raid:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "create"
    adapter: "{{ adapter }}"
    level: "{{ level }}"
    name: "{{ name }}"
  delegate_to: localhost
  tags:
    - create

- name: Delete RAID array
  fsas.primergy.irmc_raid:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "delete"
    adapter: "{{ adapter }}"
    array: "{{ array }}"
  delegate_to: localhost
  tags:
    - delete
'''

RETURN = r'''
details_for_get:
    description: If command is "get, the following value is returned.

    contains:
        configuration:
            description: list of available RAID adapters with attached logical and physical disks
            returned: always
            type: dict
            sample:
                [{
                    "id": "RAIDAdapter0",
                    "logical_drives": [{
                        "raid_level": "1",
                        "disks": [{ "slot": 0, "id": "0", "name": "WDC WD5003ABYX-", "size": "465 GB" },
                                { "slot": 1, "id": "1", "name": "WDC WD5003ABYX-", "size": "465 GB" }],
                        "id": 0,
                        "name": "LogicalDrive_0"
                    }, {
                        "raid_level": "0",
                        "disks": [{ "slot": 2, "id": "2", "name": "WDC WD5003ABYX-", "size": "465 GB" }],
                        "id": 1,
                        "name": "LogicalDrive_1"
                    }],
                    "raid_level": "0,1,5,6,10,50,60",
                    "name": "RAIDAdapter0",
                    "unused_disks": [{ "slot": 3, "id": "3", "name": "WDC WD5003ABYX-", "size": "465 GB" }]
                }]

details_for_all:
    description: For all commands, the following value is returned.

    contains:
        log:
            description: detailed log data of RAID session
            returned: in case of error
            type: dict
            sample:
                "SessionLog": {
                    "Entries": {
                        "Entry": [
                            { "#text": "CreateSession: Session 'obtainProfile' created with id 6", "@date": "2018/11/09 09:39:19" },
                            { "#text": "AttachWorkSequence: Attached work sequence 'obtainProfileParameters' to session 6", "@date": "2018/11/09 09:39:19" },
                            { "#text": "ObtainProfileParameters: Finished processing of profile path 'Server/HWConfigurationIrmc/Adapters/RAIDAdapter' with status 'Error'", "@date": "2018/11/09 09:39:45" },
                            { "#text": "TerminateSession: 'obtainProfileParameters' is being terminated", "@date": "2018/11/09 09:39:45" }
                        ]
                    },
                    "Id": 6,
                    "Tag": "",
                    "WorkSequence": "obtainProfileParameters"
                }
'''


import json

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig

# Global
result = dict()


def irmc_raid(module):
    # initialize result
    result['changed'] = False
    result['status'] = 0

    if module.check_mode:
        result['msg'] = 'module was not run'
        module.exit_json(**result)

    # initialize iRMC client
    irmc = iRMC(
        module.params['irmc_url'],
        module.params['irmc_username'],
        module.params['irmc_password'],
        validate_certs=module.params['validate_certs'],
    )

    # M8 support: Vendor detection (required)
    if irmc.vendor is None:
        result['msg'] = 'Failed to detect iRMC vendor. Vendor attribute not found in /redfish/v1'
        result['status'] = 20
        module.fail_json(**result)

    # preliminary parameter check
    preliminary_parameter_check(module, irmc)

    # get current RAID configuration
    raidadapter_profile = get_raidadapter_profile(module, irmc)
    raid_configuration = get_raid_configuration(module, irmc, raidadapter_profile)

    if module.params['command'] == 'get':
        result['configuration'] = raid_configuration

    if module.params['command'] == 'create':
        create_array(module, irmc, raid_configuration)

    if module.params['command'] == 'delete':
        delete_array(module, irmc, raid_configuration)

    module.exit_json(**result)


def preliminary_parameter_check(module, irmc):
    if module.params['command'] != 'get':
        # Get server power state
        sysdata, _headers, status = irmc.get('redfish/v1/Systems/0/')
        msg = 'OK' if status == 200 else 'Failed to get system data'
        if status < 100:
            module.fail_json(msg=msg, status=status, exception=sysdata)
        elif status != 200:
            module.fail_json(msg=msg, status=status)
        if dig(sysdata, 'PowerState') == 'On':
            result['msg'] = 'Server is powered on. Cannot continue.'
            result['status'] = 10
            module.fail_json(**result)
    if module.params['command'] == 'create' and \
       module.params['adapter'] is None and module.params['level'] is None:
        result['msg'] = "Command 'create' requires 'adapter' and 'level' to be set."
        result['status'] = 10
        module.fail_json(**result)
    if module.params['command'] == 'delete' and module.params['adapter'] is None and module.params['array'] is None:
        result['msg'] = "Command 'delete' requires 'adapter' and 'array' to be set."
        result['status'] = 11
        module.fail_json(**result)


def create_array(module, irmc, raid_configuration):
    for adapter in raid_configuration:
        if adapter['id'].replace('RAIDAdapter', '') != module.params['adapter']:
            continue
        else:
            disk_data = adapter['unused_disks']
            if not disk_data:
                result['msg'] = f"No un-used disks available on controller {module.params['adapter']}"
                result['status'] = 41
                module.fail_json(**result)

            if module.params['level'] not in adapter['level']:
                result['msg'] = (f"Adapter {module.params['adapter']} does not support RAID level {module.params['level']}. "
                                 f"Supported: {adapter['level']}")
                result['status'] = 42
                module.fail_json(**result)

            if module.params['name'] is not None:
                raid_array = {'@Action': 'Create', 'Name': module.params['name'],
                              'RaidLevel': module.params['level']}
            else:
                raid_array = {'@Action': 'Create', 'RaidLevel': module.params['level']}

            body = {
                'Server': {
                    'HWConfigurationIrmc': {
                        '@Processing': 'execute',
                        'Adapters': {
                            'RAIDAdapter': [{
                                '@AdapterId': adapter['id'],
                                '@ConfigurationType': 'Addressing',
                                'LogicalDrives': {
                                    'LogicalDrive': [raid_array],
                                },
                            }],
                        },
                        '@Version': '1.00',
                    },
                    '@Version': '1.01',
                },
            }

            # Set new configuration
            apply_raid_configuration(module, irmc, body)
            return

    result['msg'] = f"Specified adapter {module.params['adapter']} does not exist."
    result['status'] = 40
    module.fail_json(**result)


def delete_array(module, irmc, raid_configuration):
    for adapter in raid_configuration:
        if adapter['id'].replace('RAIDAdapter', '') != module.params['adapter']:
            continue
        else:
            logical_drives = adapter['logical_drives']

            if not logical_drives:
                result['msg'] = f"There are no logical drives on adapter {module.params['adapter']}."
                if module.params['array'] == '-1':
                    result['skipped'] = True
                    module.exit_json(**result)
                else:
                    result['status'] = 51
                    module.fail_json(**result)

            lds = []
            for array in logical_drives:
                if module.params['array'] != '-1' and str(array['id']) != module.params['array']:
                    ld = {'@Number': array['id'], '@Action': 'None'}
                    continue
                else:
                    ld = {'@Number': array['id'], '@Action': 'Delete'}
                lds.append(ld)

            if not lds:
                result['msg'] = f"Specified array {module.params['array']} does not exist."
                result['status'] = 52
                module.fail_json(**result)

            body = {
                'Server': {
                    'HWConfigurationIrmc': {
                        '@Processing': 'execute',
                        'Adapters': {
                            'RAIDAdapter': [{
                                '@AdapterId': adapter['id'],
                                '@ConfigurationType': 'Addressing',
                                'LogicalDrives': {
                                    'LogicalDrive': lds,
                                },
                            }],
                        },
                        '@Version': '1.00',
                    },
                    '@Version': '1.01',
                },
            }

            # Set new configuration
            apply_raid_configuration(module, irmc, body)
            return

    result['msg'] = f"Specified adapter {module.params['adapter']} does not exist."
    result['status'] = 40
    module.fail_json(**result)


def apply_raid_configuration(module, irmc, body):
    sysdata, _headers, status = irmc.post('rest/v1/Oem/eLCM/ProfileManagement/set', body)
    msg = 'OK' if status in (200, 202, 204) else 'Failed to apply RAID configuration'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=sysdata)
    elif status == 406:
        result['msg'] = f"Raid Configuration cannot be {module.params['command']}d."
        module.fail_json(msg=msg, status=status)
    elif status not in (200, 202, 204):
        module.fail_json(msg=msg, status=status)

    if module.params['wait_for_finish'] is True:
        # check that current session is terminated
        session_id = dig(sysdata, 'Session', 'Id')
        session = irmc.sessions.get(session_id)
        response = session.wait_for_finish()
        data, _headers, status = response
        msg = 'OK' if status in (200, 202, 204) else 'Session finished with error'

        if status > 30 and status < 100:
            module.fail_json(msg=msg, status=status, exception=data)
        elif status not in (200, 202, 204):
            module.fail_json(msg=msg, log=data, status=status)

    result['changed'] = True


def get_raidadapter_profile(module, irmc):
    """Remake RAIDAdapter Profile, then fetch it.
    """
    # make sure RAIDAdapter profile is up-to-date
    sysdata, _headers, status = irmc.delete('/rest/v1/Oem/eLCM/ProfileManagement/RAIDAdapter')
    msg = 'OK' if status in (200, 202, 204, 404) else 'Failed to delete RAIDAdapter profile'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=sysdata)
    elif status not in (200, 202, 204, 404):
        module.fail_json(msg=msg, status=status)

    url = 'rest/v1/Oem/eLCM/ProfileManagement/get?PARAM_PATH=Server/HWConfigurationIrmc/Adapters/RAIDAdapter'
    sysdata, _headers, status = irmc.post(url, '')
    msg = 'OK' if status in (200, 202, 204) else 'Failed to get RAID profile'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=sysdata)
    elif status == 404:
        msg = "Requested profile 'HWConfigurationIrmc/Adapters/RAIDAdapter' cannot be created."
        module.fail_json(msg=msg, status=status)
    elif status == 409:
        msg = "Requested profile 'HWConfigurationIrmc/Adapters/RAIDAdapter' already exists."
        module.fail_json(msg=msg, status=status)
    elif status not in (200, 202, 204):
        module.fail_json(msg=msg, status=status)

    if module.params['wait_for_finish'] is True:
        # check that current session is terminated
        session_id = dig(sysdata, 'Session', 'Id')
        data, _headers, status = irmc.sessions.get(session_id).wait_for_finish()
        msg = 'OK' if status in (200, 202, 204) else 'Session finished with error'
        if status > 30 and status < 100:
            module.fail_json(msg=msg, status=status, exception=data)
        elif status not in (200, 202, 204):
            module.fail_json(msg=msg, log=data, status=status)

    sysdata, _headers, status = irmc.get('/rest/v1/Oem/eLCM/ProfileManagement/RAIDAdapter', use_cache=False)
    msg = 'OK' if status == 200 else 'Failed to get RAIDAdapter profile'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=sysdata)
    elif status == 404:
        msg = "Requested profile 'HWConfigurationIrmc/Adapters/RAIDAdapter' does not exist."
        module.fail_json(msg=msg, status=status)
    elif status != 200:
        module.fail_json(msg=msg, status=status)

    return sysdata


def get_raid_configuration(module, irmc, raidadapter_profile):
    raid_configuration = []
    for adapter in dig(raidadapter_profile, 'Server', 'HWConfigurationIrmc', 'Adapters', 'RAIDAdapter', default=[]):
        adapter_list = get_adapter(module, irmc, adapter)
        physical_disks = dig(adapter, 'PhysicalDisks', 'PhysicalDisk', default=[])
        logical_drives = dig(adapter, 'LogicalDrives', 'LogicalDrive', default=[])
        for pd in physical_disks:
            disk_list = get_disk(pd)
            adapter_list['unused_disks'].append(disk_list)
        for ld in logical_drives:
            array_list = get_logicaldrive(ld)
            for ref in dig(ld, 'ArrayRefs', 'ArrayRef', default=[]):
                for array in dig(adapter, 'Arrays', 'Array', default=[]):
                    if dig(ref, '@Number') == dig(array, '@Number'):
                        for disk in dig(array, 'PhysicalDiskRefs', 'PhysicalDiskRef', default=[]):
                            for pd in physical_disks:
                                if dig(disk, '@Number') == dig(pd, '@Number'):
                                    break
                            disk_list = get_disk(pd)
                            array_list['disks'].append(disk_list)
                            if disk_list in adapter_list['unused_disks']:
                                adapter_list['unused_disks'].remove(disk_list)
            adapter_list['logical_drives'].append(array_list)
        raid_configuration.append(adapter_list)
    return raid_configuration


def get_adapter(module, irmc, adapter):
    ctrl = {}
    ctrl['id'] = dig(adapter, '@AdapterId')
    ctrl['name'] = ctrl['id']
    ctrl['level'] = dig(adapter, 'Features', 'RaidLevel')
    ctrl['logical_drives'] = []
    ctrl['unused_disks'] = []
    hwdata, _headers, status = irmc.get('redfish/v1/Systems/0/Storage?$expand=Members')
    msg = 'OK' if status == 200 else 'Failed to get Storage data'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=hwdata)
    elif status != 200:
        module.fail_json(msg=msg, status=status)
    for member in dig(hwdata, 'Members', default=[]):
        # iRMC has each StroageController with its own Storage
        for sc in dig(member, 'StorageControllers', default=[]):
            if dig(adapter, '@AdapterId').replace('RAIDAdapter', '') == dig(sc, 'MemberId'):
                ctrl['name'] = dig(sc, 'Model')
                ctrl['firmware'] = dig(sc, 'FirmwareVersion')
                ctrl['drives'] = dig(sc, 'Oem', irmc.vendor, 'DriveCount')
                ctrl['volumes'] = dig(sc, 'Oem', irmc.vendor, 'VolumeCount')
                break
    return(ctrl)


def get_logicaldrive(ld):
    logicaldrive = {}
    logicaldrive['id'] = dig(ld, '@Number')
    logicaldrive['level'] = dig(ld, 'RaidLevel')
    logicaldrive['name'] = dig(ld, 'Name')
    logicaldrive['disks'] = []
    return(logicaldrive)


def get_disk(pd):
    disk = {}
    disk['id'] = dig(pd, '@Number')
    disk['slot'] = dig(pd, 'Slot')
    disk['name'] = dig(pd, 'Product')
    disk['size'] = f"{dig(pd, 'Size', '#text')} {dig(pd, 'Size', '@Unit')}"
    return(disk)


def main():
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(required=False, type='str', default='list',
                     choices=['get', 'create', 'delete']),
        adapter=dict(required=False, type='str'),
        array=dict(required=False, type='str'),
        level=dict(required=False, type='str'),
        name=dict(required=False, type='str'),
        wait_for_finish=dict(required=False, type='bool', default=True),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_raid(module)


if __name__ == '__main__':
    main()
