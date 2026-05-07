# Manage Fsas Technologies PRIMERGY servers via iRMC with Ansible

> ⚠️ This repository was renamed from `fujitsu-ansible-irmc-integration` on April 8, 2026.
> The contents remain the same, with ongoing updates.

As of April 1, 2024, PRIMERGY servers have been transferred from Fujitsu to Fsas Technologies Inc.

## Overview

These collection and examples are intended to provide easy-to-follow and understandable solutions to manage
Fsas Technologies PRIMERGY server settings via iRMC.  
See User Guide for more details.

- [User Guide (English)](./docs/USER_GUIDE.md)
  (link to [galaxy.ansible.com](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/docs/USER_GUIDE/))
- [User Guide (Japanese)](./docs/USER_GUIDE_ja.md)
  (link to [galaxy.ansible.com](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/docs/USER_GUIDE_ja/))

## Contributing

See Contribution Guidelines for more details.

- [Contribution Guidelines (English)](./docs/CONTRIBUTING.md)
  (link to [galaxy.ansible.com](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/docs/CONTRIBUTING/))
- [Contribution Guidelines (Japanese)](./docs/CONTRIBUTING_ja.md)
  (link to [galaxy.ansible.com](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/docs/CONTRIBUTING_ja/))

## Requirements

### Hardware

- Fsas Technologies PRIMERGY Server with iRMC S6

### Software

- Python >= 3.10
- Ansible >= 2.17
- Python modules: 'requests', 'urllib3', 'requests', 'requests_toolbelt' and 'pywinrm'

## Roles

This collection provides roles for managing both iRMC settings and Windows Server 2022 configurations.  
See Configuration Guide for more details.

- [Configuration Guide (English)](./docs/CONFIGURATION.md)
  (link to [galaxy.ansible.com](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/docs/CONFIGURATION/))
- [Configuration Guide (Japanese)](./docs/CONFIGURATION_ja.md)
  (link to [galaxy.ansible.com](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/docs/CONFIGURATION_ja/))

### for iRMC

#### Update firmware

- [irmc_update_bios](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/irmc_update_bios/) - Update BIOS firmware on iRMC devices
- [irmc_update_irmc](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/irmc_update_irmc/) - Update iRMC firmware on iRMC devices

#### Configuration iRMC

- [irmc_account_admin](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/irmc_account_admin/) - Configuration settings only for the `admin` account
- [irmc_set_certificate](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/irmc_set_certificate/) - Register the SSL certificate
- [irmc_set_license](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/irmc_set_license/) - Register the license key and activate the license
- [irmc_set_ntp](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/irmc_set_ntp/) - Settings for time synchronization
- [irmc_snmp](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/irmc_snmp/) - Configure SNMP settings
- [irmc_email_alert](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/irmc_email_alert/) - Configure E-mail Alert settings

#### OS Install

- [irmc_install_windows](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/irmc_install_windows/) - Install Windows OS via iRMC virtual CD

### for Windows Server 2022

#### Configuration Windows

- [win_admin_password](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_admin_password/) - Change the password for the `Administrator` account
- [win_hostname](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_hostname/) - Change the hostname
- [win_organization_owner](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_organization_owner/) - Change the description, organization and owner
- [win_set_membership](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_set_membership/) - Join host to workgroup or domain
- [win_data_drive](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_data_drive/) - Create, resize, and delete data drives
- [win_dns](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_dns/) - Configure IPv4 DNS to the specified network adapter
- [win_locale](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_locale/) - Change language settings (language, region, time zone) for a specified account
- [win_set_rdp](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_set_rdp/) - Enable or Disable remote desktop
- [win_snmp](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_snmp/) - Enabling and configuring SNMP service

#### Install management software

- [win_serverview_agents](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_serverview_agents/) - Set up ServerView Agent
- [win_serverview_raidmanager](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_serverview_raidmanager/) - Set up ServerView RAID Manager
- [win_dsnap](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/role/win_dsnap/) - Set up DSNAP

## Modules

The following modules are part of this project:

- [irmc_biosbootorder](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_biosbootorder/) - configure iRMC to force next boot to specified option
- [irmc_cas](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_cas/) - manage iRMC CAS settings
- [irmc_certificate](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_certificate/) - manage iRMC certificates
- [irmc_compare_profiles](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_compare_profiles/) - compare two iRMC profiles
- [irmc_connectvm](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_connectvm/) - connect iRMC Virtual Media Data
- [irmc_elcm_offline_update](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_elcm_offline_update/) - offline update a server via iRMC
- [irmc_elcm_online_update](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_elcm_online_update/) - online update a server via iRMC
- [irmc_elcm_repository](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_elcm_repository/) - configure the eLCM repository in iRMC
- [irmc_eventlog](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_eventlog/) - handle iRMC eventlogs
- [irmc_facts](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_facts/) - get or set PRIMERGY server and iRMC facts
- [irmc_fwbios_update](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_fwbios_update/) - update iRMC Firmware or server BIOS
- [irmc_getvm](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_getvm/) - get iRMC Virtual Media Data
- [irmc_idled](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_idled/) - get or set server ID LED
- [irmc_ldap](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_ldap/) - manage iRMC LDAP settings
- [irmc_license](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_license/) - manage iRMC user accounts
- [irmc_ntp](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_ntp/) - manage iRMC time options
- [irmc_powerstate](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_powerstate/) - get or set server power state
- [irmc_profiles](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_profiles/) - handle iRMC profiles
- [irmc_raid](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_raid/) - handle iRMC RAID
- [irmc_scci](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_scci/) - execute iRMC remote SCCI commands
- [irmc_session](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_session/) - handle iRMC sessions
- [irmc_setnextboot](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_setnextboot/) - configure iRMC to force next boot to specified option
- [irmc_setvm](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_setvm/) - set iRMC Virtual Media Data
- [irmc_task](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_task/) - handle iRMC tasks
- [irmc_user](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/content/module/irmc_user/) - manage iRMC user accounts

### Known Issues

The `irmc_certificate` and `irmc_user` modules have usage restrictions on some M8 generation devices.
For details, refer to each module's documentation (`known_issues_on_M8` section).

## Change log

- V1.0: Initial version
- V1.1: New: iRMC FW/BIOS update, BIOS boot order, iRMC profile management
- V1.2: New: eLCM Offline/Online Update, RAID configuration
- For later versions, see [CHANGELOG.md](https://galaxy.ansible.com/ui/repo/published/fsas/primergy/docs/CHANGELOG).

## License

Copyright 2018-2026 Fsas Technologies Inc.

GNU General Public License v3.0+ (see <https://www.gnu.org/licenses/gpl-3.0.txt>)

## Contact

- <fti-autotool-ansible@dl.jp.fujitsu.com>

### Authors

- Shinya Hamano (<hamano.shinya@fujitsu.com>)
- Yutaka Kamioka (<yutaka.kamioka@fujitsu.com>)
- Tomohisa Nakai (<nakai.tomohisa@fujitsu.com>)
