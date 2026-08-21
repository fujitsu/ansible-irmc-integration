#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_idled

short_description: get or set server ID LED

description:
    - Ansible module to get or set server ID LED via iRMC RedFish interface.
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
    command:
        description: Get or set server ID LED state.
        required:    false
        default:     get
        choices:     ['get', 'set']
    state:
        description: Desired server ID LED state for command 'set', ignored otherwise.
        required:    false
        choices:     ['Off', 'Lit', 'Blinking']
'''

EXAMPLES = r'''
# Get server ID LED state
- name: Get and show server ID LED state
  tags:
    - get
  block:
    - name: Get ID LED state
      fsas.primergy.irmc_idled:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
      register: idled
      delegate_to: localhost
    - name: Show iRMC ID LED state
      ansible.builtin.debug:
        var: idled.idled_state

# Set server ID LED state
- name: Set server ID LED state
  fsas.primergy.irmc_idled:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    state: "Lit"
  delegate_to: localhost
  tags:
    - set
'''

RETURN = r'''
idled_state:
    description: server ID LED state
    returned: when command is "get"
    type: string
    sample: Blinking
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


class IdLedController:
    """ID LEDの状態を管理するControllerクラスです。
    """

    def __init__(self, irmc: iRMC, logger: Logger):
        """IdLedControllerを初期化します。

        引数:
            irmc - iRMCクライアントインスタンス
            logger - ログ出力用のLoggerインスタンス
        """
        self.irmc = irmc
        self.logger = logger

    def _fetch_current_led_state(self) -> str:
        """iRMCからID LED状態をフェッチします。

        戻り値:
            現在のLED状態

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - レスポンスにIndicatorLEDフィールドが存在しない場合
        """
        response = self.irmc.get('/redfish/v1/Systems/0')
        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        fields = ['IndicatorLED']
        state = dig(response.body, *fields)
        if state is None:
            msg = f"{'.'.join(fields)!r} field not found in response"
            self.logger.warn(msg)
            raise ModuleError(msg)

        return state

    def _fetch_allowable_led_states(self) -> list[str]:
        """iRMCから許可されたID LED状態のリストをフェッチします。

        戻り値:
            許可されたLED状態のリスト

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - レスポンスにIndicatorLED@Redfish.AllowableValuesフィールドが存在しない場合
        """
        response = self.irmc.get('/redfish/v1/Systems/0')
        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        fields = ['IndicatorLED@Redfish.AllowableValues']
        allowed_values = dig(response.body, *fields)
        if allowed_values is None:
            msg = f"{'.'.join(fields)!r} field not found in response"
            self.logger.warn(msg)
            raise ModuleError(msg)

        return allowed_values

    def get_state(self) -> ControllerResult:
        """ID LED状態を取得します。

        戻り値:
            ControllerResult（changed=False, idled_state属性を含む）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - レスポンスにIndicatorLEDフィールドが存在しない場合
        """
        self.logger.debug("Getting ID LED state from iRMC")
        state = self._fetch_current_led_state()
        return ControllerResult.unchanged(
            idled_state=state,
        )

    def set_state(self, params: Mapping[str, Any]) -> ControllerResult:
        """ID LED状態を設定します。

        引数:
            params - パラメータ辞書（必須: 'state'）

        戻り値:
            ControllerResult（changed=TrueまたはFalse）

        例外:
            ValidationError - stateパラメータが不足、または許可された値でない場合
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - レスポンスに必要なフィールドが存在しない場合
        """
        # パラメータ検証（AnsibleModuleがstr型を保証しているため型チェック不要）
        target_state = params.get('state')
        if target_state is None:
            raise ValidationError("'state' parameter is required for set command")

        self.logger.debug(f"Setting ID LED state to '{target_state}'")
        current_state = self._fetch_current_led_state()

        if current_state == target_state:
            return ControllerResult.skipped(
                msg=f"ID LED is already in state '{target_state}'",
            )

        # AllowableValuesの取得と検証
        allowed_values = self._fetch_allowable_led_states()
        if target_state not in allowed_values:
            msg = f"Invalid state '{target_state}'. Allowed: {json.dumps(allowed_values)}"
            raise ValidationError(msg)

        # 状態を設定（etagを取得）
        response = self.irmc.get('/redfish/v1/Systems/0')
        etag = dig(response.body, '@odata.etag')
        headers = {'If-Match': str(etag)} if etag else None
        body = {'IndicatorLED': target_state}
        response = self.irmc.patch('/redfish/v1/Systems/0', body, headers=headers)
        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path} with body {body}: response={response.body}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        self.logger.log(f"ID LED state changed: {current_state} -> {target_state}")
        return ControllerResult.changed_success()


def irmc_idled(module: AnsibleModule) -> None:
    """irmc_idledモジュールのメイン処理です。

    引数:
        module - AnsibleModuleインスタンス
    """
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
    controller = IdLedController(irmc, logger)

    # ビジネスロジック実行
    try:
        if module.params['command'] == 'get':
            controller_result = controller.get_state()
        elif module.params['command'] == 'set':
            controller_result = controller.set_state(module.params)
        else:
            raise ValidationError(f"Unknown command: {module.params['command']}")

        result = controller_result.to_exit_dict() | logger.to_logs_dict()
        module.exit_json(**result)

    except ModuleError as e:
        result = e.to_fail_dict() | logger.to_logs_dict()
        module.fail_json(**result)

    except Exception as e:
        # 予期しないエラー（接続エラーを含む）
        result = {'msg': f"Unexpected error: {e}", 'exception': traceback.format_exc()} | logger.to_logs_dict()
        module.fail_json(**result)


def main() -> None:
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(required=False, type='str', default='get', choices=['get', 'set']),
        state=dict(required=False, type='str', choices=['Off', 'Lit', 'Blinking']),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_idled(module)


if __name__ == '__main__':
    main()
