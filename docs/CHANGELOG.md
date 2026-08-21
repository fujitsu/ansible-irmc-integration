# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.1.0] - 2026-08-24

### Changed

- Updated the supported environment
  - Python: 3.10 or later to 3.14 or later
  - ansible-core: 2.17.14 or later to 2.21.1 or later
  - Updated dependent Python packages
- Replaced `result['warnings']` with `module.warn()` in `irmc_biosbootorder`, `irmc_setvm`
  and `irmc_fwbios_update`, following the deprecation in ansible-core 2.23
- The `irmc_email_alert` and `irmc_snmp` roles no longer pass the internal `vars`
  dictionary to their filter plugins, which will be removed in ansible-core 2.24
- Waiting for an iRMC session now has an overall timeout, retries transient connection
  errors, and writes progress to syslog so that a long-running task can be followed
- Reworked the `EXAMPLES` documentation of every module: task names, FQCN for builtin
  actions, and the `block` syntax now follow ansible-lint
- Unified how credentials are written in the example playbooks and in the `EXAMPLES`
  documentation. Values that used to look like real credentials are now placeholders
  such as `<username>` and `<password>`

### Fixed

- `irmc_setnextboot`: `bootsource: "None"` failed on some models. The request body that
  the iRMC accepts differs by model, so both known forms are now tried in order
- `irmc_setnextboot`: the returned `next_boot` reported the state before the change
- `irmc_setnextboot`: `bootmode` is now validated against the values that the iRMC
  reports as allowed, instead of being rejected by the iRMC with an unhelpful error
- `irmc_profiles`: the `EXAMPLES` documentation could not be parsed as YAML
- Fixed the example playbooks in the documentation for the `win_set_membership`,
  `irmc_snmp`, `irmc_email_alert` and `irmc_account_admin` roles. The variable names did
  not match what the roles actually read, so the examples did not work as written

### Added

- A manual test runner under `tests/manual/` for collection maintainers. It runs the
  example playbooks against real hardware before a release and keeps the output as
  evidence. It is not needed to use the collection or to contribute to it

## [3.0.1] - 2026-05-11

### Changed

- Changed Ansible collection namespace from `fujitsu.primergy` to `fsas.primergy`
  - Changed Ansible Galaxy collection page URL to `https://galaxy.ansible.com/fsas/primergy`
- Changed GitHub repository URL from `github.com/fujitsu/fujitsu-ansible-irmc-integration` to `github.com/fujitsu/ansible-irmc-integration`
- Update dependent Python packages
- Updated the development workflow to recommend uv instead of rye
  - Existing `rye sync` workflows remain available for backward compatibility
- irmc_setvm module now allows to specify "HTTPS" for share_type

### Fixed

- Variable names for workgroup and domain configuration in win_set_membership role

## [3.0.0] - 2026-02-16

### Changed

- Rebranding support for Fsas Technologies Inc.:
  - Changed Ansible collection namespace from `fujitsu.primergy` to `fsas_temp_ns.primergy`
    - `fsas_temp_ns` will be replaced after securing official namespace
  - Changed GitHub repository URL from `github.com/fujitsu/fujitsu-ansible-irmc-integration` to `github.com/{{ NEW_ORG }}/ansible-irmc-integration`
    - `{{ NEW_ORG }}` will be replaced after securing official organization
  - Updated external reference URLs, file names, document titles, and page numbers to latest versions
  - Updated Ansible collection tags
  - Updated Ansible version requirement: 8.7.0 to 10.7.0

## [2.1.0] - 2025-11-14

### Changed

- Support for PRIMERGY M8 generation in the following modules:
  - irmc_facts, irmc_powerstate, irmc_raid, irmc_fwbios_update
  - irmc_eventlog, irmc_connectvm, irmc_getvm, irmc_setvm, irmc_task

## [2.0.2] - 2025-06-26

### Fixed

- Fixed ValueError in `irmc_raid` module that could occur depending on RAID configuration.
- Fixed typos in several documentation files, including `README.md`.
- Update the contact information.

## [2.0.1] - 2024-12-10

### Changed

- Added English version of the documentation.

## [2.0.0] - 2024-11-29

### Added

- Roles and their examples based on operational scenes have been added. See `README.md` for details.
- The user guide and contribution guide have been added in Japanese.

### Fixed

- The problem that prevented setting only numeric strings for `ntp_server_primary` and `ntp_server_secondary` has been fixed in the `irmc_ntp` module.
- The `irmc_biosbootorder` module has been fixed to able the boot order to be reset with the command "default".

### Changed

- The directory structure and documents has been changed for the release to [Ansible Galaxy](https://galaxy.ansible.com/).
- The `irmc_raid` module has been verified with iRMC S6, and updated documentation.
- Python module `pywinrm` add to the requirements.

### Removed

- `DOCUMENTATION.md` is removed.

## [1.3.0] - 2024-08-30

### Changed

- Updated supported Python, Ansible, and iRMC versions.
- The note regarding the company name change has been added.
- The copyright has been changed due to organizational changes.
- The following modules have changed the type of the parameter `profile_json` from `str` to `json`.
  `irmc_profiles` and `irmc_compare_profiles`.

### Fixed

- The following modules have been fixed as not working in the latest environment.
  `irmc_user`, `irmc_powerstate`, `irmc_biosbootorder`, `irmc_ntp`, `irmc_license`, `irmc_connectvm`, `irmc_scci` and `irmc_profiles`.
- The problem BIOS update not working correctly via TFTP has been fixed in the `irmc_fwbios_update` module.
- The `irmc_fwbios_update` module fixes a problem with the ansible task not completing when updating iRMC with power on.
- Secondary NTP incorrect display is fixed in `irmc_ntp` module.

### Removed

- Since iRMC S5, FD is no longer supported as a remote media mount and cannot be specified in the following modules.
  `irmc_connectvm`, `irmc_getvm` and `irmc_setvm`.
- The `connect_fd`, `connect_cd` and `connect_hd` commands are no longer supported in the `irmc_scci` module.
- `"Floppy"` can no longer be specified for parameter `bootsource` in the `irmc_setnextboot` module.
