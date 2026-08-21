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
        description: Boot override type.
                     Ignored when bootsource is 'None'. The iRMC clears this value
                     in that case and rejects the request if it is sent.
        required:    false
        default:     Once
        choices:     ['Once', 'Continuous']
    bootmode:
        description: The mode for the next boot.
                     Ignored when bootsource is 'None', for the same reason as bootoverride.
                     Some models accept 'UEFI' only. The value is checked against the
                     AllowableValues reported by the iRMC before the request is sent.
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
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import Response, iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger, Logger


class SetNextBootController:
    """Next Boot設定を管理するControllerクラスです。"""

    # bootsource='None'(上書き解除)で iRMC が受け付けるボディは機種によって排他的に異なる。
    # 共通して通るボディは存在しないため、順に試して最初に 200 が返ったものを採用する。
    #
    # curl による実測(5機体。RedfishVersion と完全に相関した):
    #
    #   ボディ                                            1.15.0系(3台)  1.20.0系(2台)
    #   -----------------------------------------------  -------------  -------------
    #   {Target: None}                                         200            409
    #   {Target: None, Enabled: Once}                          500            409
    #   {Target: None, Enabled: Continuous}                    500            200
    #   {Target: None, Enabled: Continuous, Mode: UEFI}        500            200
    #   {Target: None, Mode: UEFI}                             500            409
    #   {Enabled: Disabled} / {Target: None, Enabled: Disabled} 400           400
    #
    #   解除後の Enabled / Mode                                null      Continuous / UEFI
    #
    # 1.15.0系は Target 単独のみ受け付け、何か添えると 500 になる。
    # 1.20.0系は Enabled='Continuous' を要求し、無いか 'Once' だと 409 になる
    # (「上書き先が無いのに次回1回だけ有効」が矛盾するという主張。Mode の有無は不問)。
    #
    # Redfish 標準の解除方法である Enabled='Disabled' は全機体で 400。
    # AllowableValues が ['Once', 'Continuous'] で、この iRMC は本当に非対応。
    #
    # RedfishVersion で分岐しないのは、5サンプルの相関で因果を確認できておらず、
    # 未知の版をどちらに寄せるかも決められないため。順に試せば版に依存しない。
    CLEAR_BODIES = (
        {'BootSourceOverrideTarget': 'None'},
        {'BootSourceOverrideTarget': 'None', 'BootSourceOverrideEnabled': 'Continuous'},
    )

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

    def _fetch_current_boot_settings(self, use_cache: bool = True) -> dict:
        """現在のBoot設定をフェッチします。

        引数:

            use_cache - iRMCクライアントのレスポンスキャッシュを使うか

        戻り値:
            Boot設定の辞書

        例外:
            HttpError - HTTPリクエストが失敗した場合

        注意事項:

            - iRMCクライアントのキャッシュはPATCH等の変更系リクエストで無効化されない
              (irmc_client.py の _cache は get() が書き込むだけ)。変更後の状態を読むときは
              use_cache=False を指定しないと変更前の値が返る
        """
        response = self.irmc.get('/redfish/v1/Systems/0', use_cache=use_cache)
        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        return dig(response.body, 'Boot', default={})

    def _patch_boot(self, boot_body: dict) -> Response:
        """Bootオブジェクトへ PATCH を送ります。

        引数:

            boot_body - 'Boot' 直下に置く辞書

        戻り値:

            Response - PATCHのレスポンス(ステータスの判定は呼び出し側の責任)
        """
        # ETagは送信直前に取得する
        response = self.irmc.get('/redfish/v1/Systems/0')
        etag = dig(response.body, '@odata.etag')
        headers = {'If-Match': str(etag)} if etag else None

        self.logger.debug(f'Setting Next Boot configuration: {boot_body}')
        return self.irmc.patch('/redfish/v1/Systems/0', {'Boot': boot_body}, headers=headers)

    def _clear_boot_source(self) -> ControllerResult:
        """ブートソースの上書きを解除します。

        受け付けられるボディが機種によって排他的に異なるため、CLEAR_BODIES を順に試し、
        最初に200が返ったものを採用します。機種差の実測結果は CLEAR_BODIES のコメントを
        参照してください。

        戻り値:

            ControllerResult - 変更ありの結果(next_bootは再取得した実際の値)

        例外:

            HttpError - どのボディも受け付けられず、状態も解除されていない場合
        """
        last_status = 0
        for boot_body in self.CLEAR_BODIES:
            last_status = self._patch_boot(boot_body).status
            if last_status == 200:
                self.logger.log('Next Boot configuration changed')
                return ControllerResult.changed_success(
                    next_boot=self._fetch_current_boot_settings(use_cache=False))

        # どのボディも200を返さなかった。ただし実測では非200でも Target は適用されるため、
        # 状態を見て判断する。既知の全形式が拒否されるのは未知のファームの可能性があるので、
        # 成功扱いにする場合も警告を残す。
        result_boot = self._fetch_current_boot_settings(use_cache=False)
        if dig(result_boot, 'BootSourceOverrideTarget') != 'None':
            msg = ('Failed to clear the boot source override. The iRMC rejected every known '
                   f'request form (last status: {last_status}).')
            self.logger.warn(msg)
            raise HttpError(msg, status=last_status)

        self.logger.warn(
            f'The iRMC rejected every known request form (last status: {last_status}), '
            'but BootSourceOverrideTarget is now None. Treating it as success.')
        return ControllerResult.changed_success(next_boot=result_boot)

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

        # BootSourceOverrideModeの検証
        # bootmode は任意なので、指定されたときだけ検証する。
        # AllowableValues を公開しない機種もあり(1.15.0系)、その場合は
        # _fetch_allowable_values() が None を返すのでこの検証は行われない。
        #
        # 実測では 'Legacy' はどちらの系でも使えなかった。違いは事前に分かるかどうかだけ:
        #   1.20.0系 -> ['UEFI'] を公開しており、ここで ValidationError にできる
        #   1.15.0系 -> 公開しないため素通しし、iRMC が 500 を返す(理由は分からない)
        # よって公開していない機種でも素通しでよい。判断材料が無いだけで、
        # 誤った値は結局 iRMC が拒否する。
        bootmode = params.get('bootmode')
        allowed_mode = self._fetch_allowable_values('BootSourceOverrideMode')
        if bootmode and allowed_mode and bootmode not in allowed_mode:
            msg = f"Invalid parameter '{bootmode}' for bootmode. Allowed: {json.dumps(allowed_mode)}"
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

            # 受け付けられるボディが機種で異なるため、CLEAR_BODIES を順に試す。
            # bootoverride / bootmode は使わない(DOCUMENTATION 参照)。
            return self._clear_boot_source()

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

        # 設定適用。'None' 以外の経路は全機体で200が返るため、非200は素直に失敗とする。
        response = self._patch_boot(boot_body)

        if response.status != 200:
            # 実際に送ったペイロードをそのまま出す('Boot' のラッパーを省かない)
            sent_body = {'Boot': boot_body}
            msg = f"Failed to {response.request.method} {response.request.path} with body {sent_body}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        self.logger.log("Next Boot configuration changed")

        # 変更後の状態は再取得する。送信ボディからの推定では実態と食い違うため。
        # Target='None' のとき iRMC は Enabled / Mode を null にするので、
        # 送っていないこの2項目が変更前の値のまま残ってしまう(実測で確認)。
        #
        # use_cache=False が必須。iRMCクライアントのキャッシュは PATCH で無効化されないため、
        # 既定のままだとこの関数の冒頭で読んだ変更前の値がそのまま返る(実機で確認)。
        return ControllerResult.changed_success(next_boot=self._fetch_current_boot_settings(use_cache=False))


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
