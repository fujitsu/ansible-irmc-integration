# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
