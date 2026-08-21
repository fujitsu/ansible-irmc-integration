irmc_snmp
=========

Configure SNMP settings for iRMC devices.

**Notes**:
For more information, refer to the following documentation:

- **English**: "Simple Network Management Protocol (SNMP)" (P.168)
  in "ServerView iRMC S6 Web Interface 3.x"  
  <https://support.ts.fujitsu.com/IndexDownload.asp?SoftwareGuid=15E0B053-4BA8-4220-A93A-98DD15C46916>

- **Japanese**: "SNMP" (P.188)
  in "ServerView iRMC S6 Web インターフェイス 3.x"  
  <https://support.ts.fujitsu.com/IndexDownload.asp?SoftwareGuid=05D99CB6-7159-4A3A-8AF6-E37537B114E8>

Requirements
------------

None

Role Variables
--------------

| Name | Required | Default Value | Choices | Type | Description |
| ---- | -------- | ------------- | ------- | ---- | ----------- |
| `snmp.enabled` | false | | | bool | Enables/disables the SNMP service. |
| `snmp.port` | false | | | int | Port on which the SNMP service is listening (normally UDP 161). |
| `snmp.protocol` | false | | `All`, `V3only` | str | SNMP protocol version to be used. If "All" is specified, all SNMP protocol versions (SNMP v1/v2c/v3) are supported. |
| `snmp.community_name` | false | | | | SNMPv1/v2c Community name |
| `snmp_trap_destination.community_name` | false | | | str | Community name used for SNMP v1/v2 trap sending. |
| `snmp_trap_destination.engine_id` | false | | | str | The Engine ID is used for sending SNMPv3 traps. |
| `snmp_trap_destination.servers[].index` | true | | 0 to 6 | int | Forwarding of SNMP traps to up to seven SNMP servers is supported. |
| `snmp_trap_destination.servers[].name` | true | | | str | DNS names or IP addresses of the servers that are configured as trap destinations. If the empty string is specified, the trap transmission will be disabled. |
| `snmp_trap_destination.servers[].protocol` | true | | `SnmpV1`, `SnmpV2c`, `SnmpV3` (*1) | str | SNMP protocol version to be used. |

- *1: `SnmpV3` can only be specified if an SNMPv3 enabled account exists.

Dependencies
------------

None

Example Playbook
----------------

playbook.yml:

    - hosts: iRMC_group
      connection: local
      gather_facts: false
      roles:
        - role: fsas.primergy.irmc_snmp
          vars:
            snmp:
              enabled: true
              protocol: "All"  # "All" or "V3only"
              community_name: "public"
            snmp_trap_destination:
              community_name: "trap-public"
              servers:
                - index: 0
                  name: "Destination1"
                  protocol: "SnmpV1"
                - index: 1
                  name: "Destination2"
                  protocol: "SnmpV2c"
                - index: 2
                  name: ""  # Empty string setting means disabling

inventory.ini:

    [iRMC_group]
    192.0.2.99 irmc_user=admin irmc_password=<password>

    [iRMC_group:vars]
    validate_certificate=false  # When iRMC deivce is operated without a server certificate

License
-------

GPL-3.0-or-later

Author Information
------------------

- Yutaka Kamioka <yutaka.kamioka@fujitsu.com>
