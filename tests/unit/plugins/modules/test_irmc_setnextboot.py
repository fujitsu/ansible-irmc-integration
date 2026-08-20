#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmc_setnextbootモジュールのユニットテストです。"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import Mock

import pytest

from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ValidationError
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import Request, Response
from ansible_collections.fsas.primergy.plugins.modules.irmc_setnextboot import SetNextBootController


class TestSetNextBootController:
    """SetNextBootControllerクラスのテストです。"""

    @pytest.fixture
    def mock_irmc(self):
        return Mock()

    @pytest.fixture
    def mock_logger(self):
        return Mock()

    @pytest.fixture
    def controller(self, mock_irmc, mock_logger):
        return SetNextBootController(mock_irmc, mock_logger)

    @pytest.fixture
    def system_response(self):
        return Response(
            body={
                'Boot': {
                    'BootSourceOverrideTarget': 'BiosSetup',
                    'BootSourceOverrideEnabled': 'Once',
                    'BootSourceOverrideMode': 'UEFI',
                    'BootSourceOverrideTarget@Redfish.AllowableValues': ['None', 'Pxe', 'Cd', 'Hdd', 'BiosSetup'],
                    'BootSourceOverrideEnabled@Redfish.AllowableValues': ['Once', 'Continuous']
                },
                '@odata.etag': 'W/"12345"',
            },
            headers={},
            status=200,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )

    def test_execute_no_change(self, controller, mock_irmc, system_response):
        """変更なしのケース"""
        mock_irmc.get.return_value = system_response

        params = {
            'bootsource': 'BiosSetup',
            'bootoverride': 'Once',
            'bootmode': 'UEFI'
        }

        result = controller.execute(params)

        assert result.changed is False
        mock_irmc.patch.assert_not_called()
        # AllowableValues(Target/Enabled/Mode の3回) + CurrentSettings(1回) = 4回
        assert mock_irmc.get.call_count == 4

    def test_execute_change_source(self, controller, mock_irmc, system_response):
        """BootSource変更のケース"""
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=200)

        params = {
            'bootsource': 'Pxe',
            'bootoverride': 'Once',
            'bootmode': 'UEFI'
        }

        result = controller.execute(params)

        assert result.changed is True
        mock_irmc.patch.assert_called_once()
        args = mock_irmc.patch.call_args
        assert args[0][1]['Boot']['BootSourceOverrideTarget'] == 'Pxe'
        # AllowableValues(3回) + CurrentSettings(1回) + ETag(1回) + 変更後の再取得(1回) = 6回
        # 最後の1回は返り値を推定せず実態を返すためのもの
        assert mock_irmc.get.call_count == 6

    def test_execute_none_source(self, controller, mock_irmc, system_response):
        """BootSource=Noneで1つ目のボディが受け付けられるケース(RedfishVersion 1.15.0系)"""
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=200)

        params = {
            'bootsource': 'None',
            'bootoverride': 'Once',  # 送られないべき
            'bootmode': 'UEFI'       # 送られないべき
        }

        result = controller.execute(params)

        assert result.changed is True
        # 200が返ったので2つ目のボディは試さない
        mock_irmc.patch.assert_called_once()
        assert mock_irmc.patch.call_args[0][1]['Boot'] == {'BootSourceOverrideTarget': 'None'}

    def test_clear_falls_back_to_second_body(self, controller, mock_irmc, system_response):
        """1つ目が拒否されたら2つ目のボディを試すこと(RedfishVersion 1.20.0系)

        1.20.0系は Target 単独を409で拒否し、Enabled='Continuous' を要求する。
        機種差の実測表は SetNextBootController.CLEAR_BODIES のコメントを参照。
        """
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.side_effect = [
            Response(body={}, headers={}, status=409),
            Response(body={}, headers={}, status=200),
        ]

        result = controller.execute({'bootsource': 'None', 'bootoverride': 'Once', 'bootmode': 'UEFI'})

        assert result.changed is True
        assert mock_irmc.patch.call_count == 2
        sent = [c[0][1]['Boot'] for c in mock_irmc.patch.call_args_list]
        assert sent == [
            {'BootSourceOverrideTarget': 'None'},
            {'BootSourceOverrideTarget': 'None', 'BootSourceOverrideEnabled': 'Continuous'},
        ]

    def test_clear_succeeds_when_state_cleared_despite_errors(self, controller, mock_irmc, system_response):
        """全ボディが拒否されても、状態が解除済みなら成功として扱うこと

        実測では非200でも Target は適用される。未知のファームでも取りこぼさないための保険。
        """
        cleared = Response(
            body={'Boot': {'BootSourceOverrideTarget': 'None',
                           'BootSourceOverrideEnabled': None,
                           'BootSourceOverrideMode': None},
                  '@odata.etag': 'W/"12345"'},
            headers={}, status=200, request=Request('GET', '/redfish/v1/Systems/0'),
        )
        # 最初の4回(AllowableValues 3回 + 現在値)は変更前、以降は解除済みを返す
        mock_irmc.get.side_effect = [system_response] * 4 + [cleared] * 10
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=500)

        result = controller.execute({'bootsource': 'None', 'bootoverride': 'Once', 'bootmode': 'UEFI'})

        assert result.changed is True
        assert mock_irmc.patch.call_count == len(controller.CLEAR_BODIES)
        controller.logger.warn.assert_called()

    def test_clear_fails_when_state_not_cleared(self, controller, mock_irmc, system_response):
        """全ボディが拒否され、状態も解除されていなければ失敗すること"""
        mock_irmc.get.return_value = system_response  # Target は BiosSetup のまま
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=500)

        with pytest.raises(HttpError) as exc:
            controller.execute({'bootsource': 'None', 'bootoverride': 'Once', 'bootmode': 'UEFI'})

        assert exc.value.status == 500
        assert mock_irmc.patch.call_count == len(controller.CLEAR_BODIES)

    def test_non_clear_does_not_retry(self, controller, mock_irmc, system_response):
        """'None' 以外の経路は緩和しないこと(1回で失敗させる)"""
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=500)

        with pytest.raises(HttpError):
            controller.execute({'bootsource': 'Pxe', 'bootoverride': 'Once', 'bootmode': 'UEFI'})

        mock_irmc.patch.assert_called_once()

    def test_failure_message_shows_sent_payload(self, controller, mock_irmc, system_response):
        """失敗メッセージが実際に送ったペイロードを示すこと

        'Boot' のラッパーを省くと、バグ報告に貼られた文字列から実際のリクエストが
        再現できなくなる。
        """
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=500)

        with pytest.raises(HttpError) as exc:
            controller.execute({'bootsource': 'Cd', 'bootoverride': 'Once', 'bootmode': 'Legacy'})

        sent = mock_irmc.patch.call_args[0][1]
        assert str(sent) in str(exc.value)
        assert "{'Boot':" in str(exc.value)

    def test_execute_refetches_without_cache(self, controller, mock_irmc, system_response):
        """変更後の再取得がキャッシュを迂回すること

        iRMCクライアントのキャッシュはPATCHで無効化されないため、既定のまま再取得すると
        変更前の値が返る。実機でnext_bootが1回分ずれる不具合として現れた。
        """
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=200)

        controller.execute({'bootsource': 'Pxe', 'bootoverride': 'Once', 'bootmode': 'UEFI'})

        # PATCH後の最後のGETだけが use_cache=False であること
        assert mock_irmc.get.call_args.kwargs.get('use_cache') is False
        # それ以前のGETはキャッシュを使ってよい(同一リクエストの重複送信を避けるため)。
        # None は use_cache を渡していない呼び出し(AllowableValues 3回 と ETag 1回)。
        assert [c.kwargs.get('use_cache') for c in mock_irmc.get.call_args_list] == [
            None, None, None, True, None, False
        ]

    def test_validation_error_mode(self, controller, mock_irmc):
        """AllowableValues に無い bootmode を弾くこと

        1.20.0系は BootSourceOverrideMode@Redfish.AllowableValues に ['UEFI'] だけを
        公開する。Legacy を渡すと iRMC まで届く前にここで落ちる。
        """
        uefi_only = Response(
            body={'Boot': {'BootSourceOverrideTarget': 'BiosSetup',
                           'BootSourceOverrideEnabled': 'Once',
                           'BootSourceOverrideMode': 'UEFI',
                           'BootSourceOverrideTarget@Redfish.AllowableValues': ['None', 'Cd', 'BiosSetup'],
                           'BootSourceOverrideEnabled@Redfish.AllowableValues': ['Once', 'Continuous'],
                           'BootSourceOverrideMode@Redfish.AllowableValues': ['UEFI']},
                  '@odata.etag': 'W/"12345"'},
            headers={}, status=200, request=Request('GET', '/redfish/v1/Systems/0'),
        )
        mock_irmc.get.return_value = uefi_only

        with pytest.raises(ValidationError):
            controller.execute({'bootsource': 'Cd', 'bootoverride': 'Once', 'bootmode': 'Legacy'})

        mock_irmc.patch.assert_not_called()

    def test_mode_not_validated_when_not_advertised(self, controller, mock_irmc, system_response):
        """AllowableValues を公開しない機種では bootmode を検証しないこと

        1.15.0系は BootSourceOverrideMode@Redfish.AllowableValues を持たない。
        判断材料が無いので素通しし、iRMC の判断に委ねる。
        """
        mock_irmc.get.return_value = system_response  # Mode の AllowableValues は無い
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=200)

        result = controller.execute({'bootsource': 'Cd', 'bootoverride': 'Once', 'bootmode': 'Legacy'})

        assert result.changed is True
        assert mock_irmc.patch.call_args[0][1]['Boot']['BootSourceOverrideMode'] == 'Legacy'

    def test_validation_error_source(self, controller, mock_irmc, system_response):
        """不正なBootSourceのケース"""
        mock_irmc.get.return_value = system_response

        params = {
            'bootsource': 'InvalidSource',
            'bootoverride': 'Once'
        }

        with pytest.raises(ValidationError) as exc:
            controller.execute(params)

        assert "Invalid parameter 'InvalidSource'" in exc.value.message

    def test_validation_error_override(self, controller, mock_irmc, system_response):
        """不正なBootOverrideのケース"""
        mock_irmc.get.return_value = system_response

        params = {
            'bootsource': 'BiosSetup',
            'bootoverride': 'InvalidOverride'
        }

        with pytest.raises(ValidationError) as exc:
            controller.execute(params)

        assert "Invalid parameter 'InvalidOverride'" in exc.value.message

    def test_http_error_get(self, controller, mock_irmc):
        """GET失敗のケース"""
        mock_irmc.get.return_value = Response(body='', headers={}, status=500)

        with pytest.raises(HttpError) as exc:
            controller.execute({'bootsource': 'BiosSetup'})

        assert exc.value.status == 500

    def test_http_error_patch(self, controller, mock_irmc, system_response):
        """PATCH失敗のケース"""
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.return_value = Response(body='', headers={}, status=500)

        params = {
            'bootsource': 'Pxe',
            'bootoverride': 'Once'
        }

        with pytest.raises(HttpError) as exc:
            controller.execute(params)

        assert exc.value.status == 500
