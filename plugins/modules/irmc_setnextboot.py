#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_setnextboot

short_description: configure iRMC to force next boot to specified option

description:
    - Ansible module to configure iRMC to force next boot to specified option.
    - Module Version V2.0.0.

requirements:
    - The module needs to run locally.
    - iRMC S6.
    - Python >= 3.14
    - Python modules 'requests', 'urllib3'

version_added: "2.4"

author:
    - Yutaka Kamioka (<yutaka.kamioka@fujitsu.com>)

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
    bootsource:
        description: The source for the next boot.
        required:    false
        default:     BiosSetup
        choices:     ['None', 'Pxe', 'Cd', 'Hdd', 'BiosSetup']
    bootoverride:
        description: Boot override type. If bootsource is 'None', it is ignored.
        required:    false
        default:     Once
        choices:     ['Once', 'Continuous']
    bootmode:
        description: The mode for the next boot. If bootsource is 'None', it is ignored.
        required:    false
        choices:     ['Legacy', 'UEFI']
'''

EXAMPLES = r'''
# Set Bios to boot from the specified device.
# Note: boot from virtual CD might fail, if a 'real' DVD drive exists
- name: Set Bios to boot from the specified device.
  fsas.primergy.irmc_setnextboot:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    bootsource: "{{ bootsource }}"
    bootoverride: "{{ bootoverride | default('Once') }}"
    bootmode: "UEFI"
  delegate_to: localhost
'''

RETURN = r'''
next_boot:
    description: Current next boot configuration
    returned: always
    type: dict
    contains:
        BootSourceOverrideTarget:
            description: The source for the next boot
            type: string
            sample: BiosSetup
        BootSourceOverrideEnabled:
            description: Boot override type
            type: string
            sample: Once
        BootSourceOverrideMode:
            description: The mode for the next boot
            type: string
            sample: UEFI
'''


import json
import traceback
from typing import Any, Mapping

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.controller_result import ControllerResult
from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ModuleError, ValidationError
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger, Logger


class SetNextBootController:
    """Next Boot設定を管理するControllerクラスです。"""

    def __init__(self, irmc: iRMC, logger: Logger):
        """SetNextBootControllerを初期化します。

        引数:
            irmc - iRMCクライアントインスタンス
            logger - ログ出力用のLoggerインスタンス
        """
        self.irmc = irmc
        self.logger = logger

    def _fetch_allowable_values(self, key: str) -> list[str] | None:
        """指定されたキーのAllowableValuesをフェッチします。

        引数:
            key - AllowableValuesを取得するプロパティ名（例: 'BootSourceOverrideTarget'）

        戻り値:
            AllowableValuesのリスト。存在しない場合はNone。

        例外:
            HttpError - HTTPリクエストが失敗した場合
        """
        response = self.irmc.get('/redfish/v1/Systems/0')
        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        return dig(response.body, 'Boot', f'{key}@Redfish.AllowableValues')

    def _fetch_current_boot_settings(self) -> dict:
        """現在のBoot設定をフェッチします。

        戻り値:
            Boot設定の辞書

        例外:
            HttpError - HTTPリクエストが失敗した場合
        """
        response = self.irmc.get('/redfish/v1/Systems/0')
        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        return dig(response.body, 'Boot', default={})

    def execute(self, params: Mapping[str, Any]) -> ControllerResult:
        """Next Boot設定を実行します。

        引数:
            params - パラメータ辞書

        戻り値:
            ControllerResult
        """
        # BootSourceOverrideTargetの検証
        bootsource = params.get('bootsource')
        allowed_source = self._fetch_allowable_values('BootSourceOverrideTarget')
        if allowed_source and bootsource not in allowed_source:
            msg = f"Invalid parameter '{bootsource}' for bootsource. Allowed: {json.dumps(allowed_source)}"
            raise ValidationError(msg)

        # BootSourceOverrideEnabledの検証
        bootoverride = params.get('bootoverride')
        allowed_override = self._fetch_allowable_values('BootSourceOverrideEnabled')
        if allowed_override and bootoverride not in allowed_override:
            msg = f"Invalid parameter '{bootoverride}' for bootoverride. Allowed: {json.dumps(allowed_override)}"
            raise ValidationError(msg)

        # 現在の設定を取得
        self.logger.debug("Getting current boot settings from iRMC")
        current_boot = self._fetch_current_boot_settings()
        current_source = dig(current_boot, 'BootSourceOverrideTarget')
        current_override = dig(current_boot, 'BootSourceOverrideEnabled')
        current_mode = dig(current_boot, 'BootSourceOverrideMode')

        # 目標設定を構築
        target_source = params.get('bootsource')
        target_override = params.get('bootoverride')
        target_mode = params.get('bootmode')

        # 変更が必要か判定
        if target_source == 'None':
            if current_source == 'None':
                return ControllerResult.unchanged(next_boot=current_boot)

            # リクエストボディ構築
            body = {'Boot': {'BootSourceOverrideTarget': 'None'}}
        else:
            # 変更判定
            changes_needed = False
            if current_source != target_source:
                changes_needed = True
            if current_override != target_override:
                changes_needed = True
            if target_mode and current_mode != target_mode:
                changes_needed = True

            if not changes_needed:
                return ControllerResult.unchanged(next_boot=current_boot)

            # リクエストボディ構築
            boot_body = {
                'BootSourceOverrideTarget': target_source,
                'BootSourceOverrideEnabled': target_override
            }
            if target_mode:
                boot_body['BootSourceOverrideMode'] = target_mode
            body = {'Boot': boot_body}

        # 設定適用（ETag取得）
        response = self.irmc.get('/redfish/v1/Systems/0')
        etag = dig(response.body, '@odata.etag')
        headers = {'If-Match': str(etag)} if etag else None

        self.logger.debug(f"Setting Next Boot configuration: {body}")
        response = self.irmc.patch('/redfish/v1/Systems/0', body, headers=headers)

        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path} with body {body}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        self.logger.log("Next Boot configuration changed")

        # 変更後の状態を返す（推定値）
        result_boot = current_boot.copy()
        result_boot.update(body['Boot'])
        return ControllerResult.changed_success(next_boot=result_boot)


def irmc_setnextboot(module: AnsibleModule) -> None:
    """irmc_setnextbootモジュールのメイン処理です。"""
    if module.check_mode:
        module.exit_json(changed=False, msg='module was not run')

    # ロガー初期化
    logger = AnsibleLogger(module)

    # iRMCクライアント初期化
    irmc = iRMC(
        ipaddress=module.params['irmc_url'],
        username=module.params['irmc_username'],
        password=module.params['irmc_password'],
        validate_certs=module.params['validate_certs'],
        logger=logger,
        raise_on_error=True,
    )

    # Controller初期化
    controller = SetNextBootController(irmc, logger)

    # ビジネスロジック実行
    try:
        controller_result = controller.execute(module.params)
        result = controller_result.to_exit_dict() | logger.to_logs_dict()
        module.exit_json(**result)

    except ModuleError as e:
        result = e.to_fail_dict() | logger.to_logs_dict()
        module.fail_json(**result)

    except Exception as e:
        result = {'msg': f"Unexpected error: {e}", 'exception': traceback.format_exc()} | logger.to_logs_dict()
        module.fail_json(**result)


def main() -> None:
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        bootsource=dict(required=False, type='str', default='BiosSetup',
                        choices=['None', 'Pxe', 'Cd', 'Hdd', 'BiosSetup']),
        bootoverride=dict(required=False, type='str', default='Once', choices=['Once', 'Continuous']),
        bootmode=dict(required=False, type='str', choices=['Legacy', 'UEFI']),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_setnextboot(module)


if __name__ == '__main__':
    main()
