#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_facts

short_description: get or set PRIMERGY server and iRMC facts

description:
    - Ansible module to get or set basic iRMC and PRIMERGY server data via iRMC RedFish interface.
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
        type:        bool
        required:    false
        default:     true
    command:
        description: How to access server facts.
        required:    false
        default:     get
        choices:     ['get', 'set']
    asset_tag:
        description: Server asset tag.
        required:    false
    location:
        description: Server location.
        required:    false
    description:
        description: Server description.
        required:    false
    contact:
        description: System contact.
        required:    false
    helpdesk_message:
        description: Help desk message.
        required:    false
'''

EXAMPLES = r'''
# Get basic server and iRMC facts
- name: Get and show basic server and iRMC facts
  tags:
    - get
  block:
    - name: Get basic server and iRMC facts
      fsas.primergy.irmc_facts:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
      register: result
      delegate_to: localhost
    - name: Show server and iRMC facts
      ansible.builtin.debug:
        var: result.facts

# Set server asset tag
- name: Set server asset tag
  fsas.primergy.irmc_facts:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    asset_tag: "Ansible test server"
  delegate_to: localhost
  tags:
    - set
'''

RETURN = r'''
details:
    description:
        If command is "get", the following values are returned.

        If command is "set", the default return value of Ansible (changed, failed, etc.) is returned.

    contains:
        hardware.ethernetinterfaces:
            description:
                dict with total number (count)
                and list of ethernet interfaces (devices)
                with relevant data (id, macaddress, name).
            returned: always
            type: dict
            sample:
                {
                    "count": 2,
                    "devices": [
                        { "id": "0", "macaddress": "01:02:03:04:05:06", "name": "eth0" },
                        { "id": "1", "macaddress": "01:02:03:04:05:06", "name": "eth1" }
                    ]
                }
        hardware.fans:
            description:
                dict with available fan slots (sockets)
                and total number (count)
                and list of existing fans (devices)
                with relevant data (id, manufacturer, name, size).
                note that fan devices are only returned if server is 'On'.
            returned: always
            type: dict
            sample:
                {
                    "count": 2,
                    "devices": [
                        { "id": "0", "manufacturer": "Micron Technology", "name": "DIMM-1A", "size": 8192 },
                        { "id": "12", "manufacturer": "SK Hynix", "name": "DIMM-1E", "size": 16384 }
                    ],
                    "sockets": 24
                }
        hardware.memory:
            description:
                dict with available memory slots (sockets)
                and total number (count)
                and list of existing memories (devices)
                with relevant data (id, manufacturer, name, size).
            returned: always
            type: dict
            sample:
                {
                    "count": 6,
                    "devices": [
                        { "id": "0", "location": "SystemBoard", "name": "FAN1 SYS" },
                        { "id": "1", "location": "SystemBoard", "name": "FAN2 SYS" },
                        { "id": "2", "location": "SystemBoard", "name": "FAN3 SYS" },
                        { "id": "3", "location": "SystemBoard", "name": "FAN4 SYS" },
                        { "id": "4", "location": "SystemBoard", "name": "FAN5 SYS" },
                        { "id": "5", "location": "PowerSupply", "name": "FAN PSU1" }
                    ],
                    "sockets": 7
                }
        hardware.powersupplies:
            description:
                dict with available power supply slots (sockets)
                and total number (count)
                and list of existing power supplies (devices)
                with relevant data (id, manufacturer, model, name).
            returned: always
            type: dict
            sample:
                {
                    "count": 1,
                    "devices": [
                        { "id": "0", "manufacturer": "CHICONY", "model": "S13-450P1A", "name": "PSU1" }
                    ],
                    "sockets": 2
                }
        hardware.processors:
            description:
                dict with available processor slots (sockets)
                and total number (count)
                and list of existing processors (devices)
                with relevant data (cores, id, name, threads).
            returned: always
            type: dict
            sample:
                {
                    "count": 2,
                    "devices": [
                        { "cores": 6, "id": "0", "name": "Genuine Intel(R) CPU @ 2.00GHz", "threads": 6 },
                        { "cores": 6, "id": "1", "name": "Genuine Intel(R) CPU @ 2.00GHz", "threads": 6 }
                    ],
                    "sockets": 2
                }
        hardware.storagecontrollers:
            description:
                dict with total number (count)
                and list of storage controllers (devices)
                with relevant data (drives, firmware, id, name, volume).
                note that storage controllers are only returned if server is 'On'.
            returned: always
            type: dict
            sample:
                {
                    "count": 1,
                    "devices": [
                        { "drives": 4, "firmware": "4.270.00-4869", "id": "1000", "name": "PRAID EP400i", "volumes": 1 }
                    ]
                }
        irmc:
            description:
                dict with relevant iRMC data
                (fw_builddate, fw_running, fw_version, hostname, macaddress, sdrr_version).
            returned: always
            type: dict
            sample:
                {
                    "fw_builddate": "2018-03-05T14:02:44",
                    "fw_running": "LowFWImage",
                    "fw_version": "9.08F",
                    "hostname": "iRMC01CA5C-iRMC",
                    "macaddress": "90:1B:0E:01:CA:5C",
                    "sdrr_version": "3.73"
                }
        mainboard:
            description:
                dict with relevant mainboard data
                (dnumber, manufacturer, part_number, serial_number, version).
            returned: always
            type: dict
            sample:
                {
                    "dnumber": "D3289",
                    "manufacturer": "Fsas Technologies",
                    "part_number": "S26361-D3289-D13",
                    "serial_number": "44617895",
                    "version": "WGS04 GS50"
                }
        system:
            description:
                dict with relevant system data
                (asset_tag, bios_version, description, health, helpdesk_message, host_name,
                idled_state, ip, location, manufacturer, memory_size, model, part_number,
                power_state, serial_number, uuid).
            returned: always
            type: dict
            sample:
                {
                    "asset_tag": "New AssetTag",
                    "bios_version": "V5.0.0.9 R1.36.0 for D3289-A1x",
                    "contact": "Admin (admin@server.room)",
                    "description": "server description",
                    "health": "OK",
                    "helpdesk_message": "New helpdesk message",
                    "host_name": "STK-SLES11SP4x64",
                    "idled_state": "Off",
                    "ip": 101.102.103.104,
                    "location": "Server Room",
                    "manufacturer": "Fsas Technologies",
                    "memory_size": "24 GB",
                    "model": "PRIMERGY RX2540 M1",
                    "part_number": "ABN:K1495-VXXX-XX",
                    "power_state": "On",
                    "serial_number": "YLVT000098",
                    "uuid": "11223344-5566-cafe-babe-deadbeef1234"
                }
'''


import json

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger


def irmc_facts(module):
    result = dict(
        changed=False,
        status=0,
    )

    if module.check_mode:
        result['msg'] = 'module was not run'
        module.exit_json(**result)

    # parameter check
    if module.params['command'] == 'set':
        if module.params['asset_tag'] is None and module.params['description'] is None and \
           module.params['helpdesk_message'] is None and module.params['location'] is None and \
           module.params['contact'] is None:
            result['msg'] = "Command 'set' requires at least one parameter to be set!"
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
        logger=logger
    )

    # M8 support: Vendor detection (required)
    if irmc.vendor is None:
        result['msg'] = 'Failed to detect iRMC vendor. Vendor attribute not found in /redfish/v1'
        result['status'] = 20
        module.fail_json(**result)

    # Get iRMC OEM system data
    oem_path = f'redfish/v1/Systems/0/Oem/{irmc.vendor}/System'
    oemdata, _headers, status = irmc.get(oem_path)
    msg = 'OK' if status == 200 else f'Failed to get OEM data from {oem_path}'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=oemdata)
    elif status != 200:
        module.fail_json(msg=msg, status=status)

    if module.params['command'] == 'get':
        # Get iRMC system data
        sysdata, _headers, status = irmc.get('redfish/v1/Systems/0/')
        msg = 'OK' if status == 200 else 'Failed to get system data'
        if status < 100:
            module.fail_json(msg=msg, status=status, exception=sysdata)
        elif status != 200:
            module.fail_json(msg=msg, status=status)
        power_state = dig(sysdata, 'PowerState')

        # Get iRMC FW data
        fw_path = f'redfish/v1/Systems/0/Oem/{irmc.vendor}/FirmwareInventory'
        fwdata, _headers, status = irmc.get(fw_path)
        msg = 'OK' if status == 200 else f'Failed to get firmware data from {fw_path}'
        if status < 100:
            module.fail_json(msg=msg, status=status, exception=fwdata)
        elif status != 200:
            module.fail_json(msg=msg, status=status)

        result['facts'] = setup_resultdata(sysdata, oemdata, fwdata, irmc.vendor)
        result = add_system_hw_info(power_state, module, irmc, result)
        result = add_chassis_hw_info(module, irmc, result)
        result = add_irmc_hw_info(module, irmc, result)
        module.exit_json(**result)

    # Set iRMC OEM system data
    body = setup_facts(module.params)
    etag = dig(oemdata, '@odata.etag')

    # Validate etag
    if not etag or not str(etag).isdigit():
        module.fail_json(msg=f'Invalid etag: {etag}', status=97)

    # PATCH OEM data
    oem_patch_path = f'redfish/v1/Systems/0/Oem/{irmc.vendor}/System/'
    headers = {'If-Match': str(etag)}
    patch, _headers, status = irmc.patch(oem_patch_path, body, headers=headers)
    msg = 'OK' if status == 200 else f'Failed to update OEM data at {oem_patch_path}'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=patch)
    elif status != 200:
        module.fail_json(msg=msg, status=status)

    result['changed'] = True
    module.exit_json(**result)


def add_system_hw_info(power_state, module, irmc, result):
    # get system hardware
    for hw in ('Memory', 'Processors', 'EthernetInterfaces', 'Storage'):
        hwdata, _headers, status = irmc.get(f'redfish/v1/Systems/0/{hw}?$expand=Members')
        msg = 'OK' if status == 200 else f'Failed to get {hw}'
        if status < 100:
            module.fail_json(msg=msg, status=status, exception=hwdata)
        elif status != 200:
            module.fail_json(msg=msg, status=status)
        items = 0
        hw_dict = {}
        hw_dict['devices'] = []
        for member in dig(hwdata, 'Members', default=[]):
            hw_list = {}
            if dig(member, 'Status', 'State') == 'Enabled':
                if hw == 'Memory':
                    hw_list['id'] = dig(member, 'Id')
                    hw_list['name'] = dig(member, 'DeviceLocator')
                    hw_list['manufacturer'] = dig(member, 'Manufacturer')
                    hw_list['size'] = dig(member, 'CapacityMiB')
                if hw == 'Processors':
                    hw_list['id'] = dig(member, 'Id')
                    hw_list['name'] = dig(member, 'Model')
                    hw_list['cores'] = dig(member, 'TotalCores')
                    hw_list['threads'] = dig(member, 'TotalThreads')
                if hw == 'EthernetInterfaces':
                    hw_list['id'] = dig(member, 'Id')
                    hw_list['name'] = dig(member, 'Description')
                    if not hw_list['name']:
                        hw_list['name'] = f"{dig(member, 'Name')} {hw_list['id']}"
                    hw_list['macaddress'] = dig(member, 'MACAddress')
                if hw == 'Storage' and power_state == 'On':
                    # iRMC has each StroageController with its own Storage
                    for ctrl in dig(member, 'StorageControllers', default=[]):
                        hw_list['id'] = dig(member, 'Id')
                        hw_list['name'] = dig(ctrl, 'Model')
                        hw_list['firmware'] = dig(ctrl, 'FirmwareVersion')
                        hw_list['drives'] = dig(ctrl, 'Oem', irmc.vendor, 'DriveCount')
                        hw_list['volumes'] = dig(ctrl, 'Oem', irmc.vendor, 'VolumeCount')
                items += 1
                if hw_list:
                    hw_dict['devices'].append(hw_list)
        hw_dict['count'] = items
        if hw == 'Storage':
            hw = 'StorageControllers'
        if hw in ('Memory', 'Processors'):
            hw_dict['sockets'] = dig(hwdata, 'Members@odata.count')
        result['facts']['hardware'][hw.lower()] = hw_dict
    return result


def add_chassis_hw_info(module, irmc, result):
    # get chassis hardware
    hw_source = {
        'redfish/v1/Chassis/0/Thermal#/Fans': ['Fans'],
        'redfish/v1/Chassis/0/Power#/PowerSupplies': ['PowerSupplies'],
    }
    for hw_link, hw_list in hw_source.items():
        hwdata, _headers, status = irmc.get(hw_link)
        msg = 'OK' if status == 200 else f'Failed to get chassis hardware from {hw_link}'
        if status < 100:
            module.fail_json(msg=msg, status=status, exception=hwdata)
        elif status != 200:
            module.fail_json(msg=msg, status=status)
        for hw in hw_list:
            items = 0
            hw_dict = {}
            hw_dict['devices'] = []
            for member in dig(hwdata, hw, default=[]):
                hw_list = {}
                if dig(member, 'Status', 'State') == 'Enabled':
                    if hw == 'PowerSupplies':
                        hw_list['id'] = dig(member, 'MemberId')
                        hw_list['name'] = dig(member, 'Name')
                        hw_list['manufacturer'] = dig(member, 'Manufacturer')
                        hw_list['model'] = dig(member, 'Model')
                    elif hw == 'Voltages':
                        hw_list['id'] = dig(member, 'MemberId')
                        hw_list['name'] = dig(member, 'Name')
                    else:
                        hw_list['id'] = dig(member, 'MemberId')
                        hw_list['name'] = dig(member, 'Name')
                        hw_list['location'] = dig(member, 'PhysicalContext')
                    items += 1
                    if hw_list:
                        hw_dict['devices'].append(hw_list)
            hw_dict['count'] = items
            hw_dict['sockets'] = dig(hwdata, f'{hw}@odata.count')
            result['facts']['hardware'][hw.lower()] = hw_dict
    return result


def add_irmc_hw_info(module, irmc, result):
    # get iRMC info
    hwdata, _headers, status = irmc.get('redfish/v1/Managers/iRMC/EthernetInterfaces?$expand=Members')
    msg = 'OK' if status == 200 else 'Failed to get iRMC network info'
    if status < 100:
        module.fail_json(msg=msg, status=status, exception=hwdata)
    elif status != 200:
        module.fail_json(msg=msg, status=status)
    for member in dig(hwdata, 'Members', default=[]):
        result['facts']['irmc']['macaddress'] = dig(member, 'MACAddress')
        result['facts']['irmc']['hostname'] = dig(member, 'HostName')
    return result


def setup_facts(data):
    body = dict()
    if data['asset_tag'] is not None:
        body['AssetTag'] = data['asset_tag']
    if data['location'] is not None:
        body['Location'] = data['location']
    if data['description'] is not None:
        body['Description'] = data['description']
    if data['contact'] is not None:
        body['Contact'] = data['contact']
    if data['helpdesk_message'] is not None:
        body['HelpdeskMessage'] = data['helpdesk_message']
    return body


def setup_resultdata(data, data2, data3, vendor):
    data = {
        'system': {
            'bios_version': dig(data, 'BiosVersion'),
            'idled_state': dig(data, 'IndicatorLED'),
            'asset_tag': dig(data2, 'AssetTag'),
            'host_name': dig(data, 'HostName'),
            'manufacturer': dig(data, 'Manufacturer'),
            'model': dig(data, 'Model'),
            # 'name': dig(data, "Name"),
            'part_number': dig(data, 'PartNumber'),
            'serial_number': dig(data, 'SerialNumber'),
            'uuid': dig(data, 'UUID'),
            'ip': dig(data2, 'SystemIP'),
            'location': dig(data2, 'Location'),
            'description': dig(data2, 'Description'),
            'contact': dig(data2, 'Contact'),
            'helpdesk_message': dig(data2, 'HelpdeskMessage'),
            'power_state': dig(data, 'PowerState'),
            'memory_size': f"{dig(data, 'MemorySummary', 'TotalSystemMemoryGiB', default=0)} GB",
            'health': dig(data, 'Status', 'HealthRollup'),
        },
        'mainboard': {
            'manufacturer': dig(data, 'Oem', vendor, 'MainBoard', 'Manufacturer'),
            'dnumber': dig(data, 'Oem', vendor, 'MainBoard', 'Model'),
            'part_number': dig(data, 'Oem', vendor, 'MainBoard', 'PartNumber'),
            'serial_number': dig(data, 'Oem', vendor, 'MainBoard', 'SerialNumber'),
            'version': dig(data, 'Oem', vendor, 'MainBoard', 'Version'),
        },
        'irmc': {
            'fw_version': dig(data3, 'BMCFirmware'),
            'fw_builddate': dig(data3, 'BMCFirmwareBuildDate'),
            'fw_running': dig(data3, 'BMCFirmwareRunning'),
            'sdrr_version': dig(data3, 'SDRRVersion'),
        },
        'hardware': {
        },
    }
    return data


def main():
    # import pdb; pdb.set_trace()
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(required=False, type='str', default='get', choices=['get', 'set']),
        asset_tag=dict(required=False, type='str'),
        location=dict(required=False, type='str'),
        description=dict(required=False, type='str'),
        contact=dict(required=False, type='str'),
        helpdesk_message=dict(required=False, type='str'),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_facts(module)


if __name__ == '__main__':
    main()
