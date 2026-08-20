#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmcモジュールのユニットテスト

waitForSessionToFinish() のタイムアウト・通信エラーのリトライ・進捗ログを対象とします。
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import Mock, patch

import pytest

from ansible_collections.fsas.primergy.plugins.module_utils import irmc


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def module():
    """AnsibleModule のモック"""
    mod = Mock()
    mod.params = {'irmc_url': '192.0.2.1'}
    return mod


def response(session_status):
    """sessionInformation/<id>/status のレスポンスを模したモックを返します。

    引数:

        session_status - Session.Status に入れる文字列

    戻り値:

        Mock - .json() が該当の辞書を返すモック
    """
    res = Mock()
    res.json.return_value = {'Session': {'Status': session_status}}
    return res


@pytest.fixture
def no_sleep():
    """time.sleep を無効化し、time.time を呼び出しごとに10秒進める

    ポーリング待ちを実時間なしで再現するためのフィクスチャです。
    """
    clock = {'now': 1000.0}

    def fake_time():
        clock['now'] += 10.0
        return clock['now']

    with patch.object(irmc.time, 'sleep'), patch.object(irmc.time, 'time', side_effect=fake_time):
        yield


# ========================================
# 従来の挙動（回帰）
# ========================================


class TestWaitForSessionToFinishExistingBehaviour:
    """変更前から期待されている挙動"""

    def test_session_terminated(self, module, no_sleep):
        """terminated ならそのまま成功で返る"""
        res = response('terminated')
        with patch.object(irmc, 'irmc_redfish_get', return_value=(200, res, 'OK')):
            status, data, msg = irmc.waitForSessionToFinish(module, 1)

        assert status == 200
        assert data is res
        assert msg == 'Session result: terminated'

    def test_session_terminated_with_error(self, module, no_sleep):
        """terminated with error なら status 29 とログの内容を返す"""
        res = response('terminated with error')
        log = Mock()
        log.json.return_value = {'SessionLog': 'detail'}
        with patch.object(irmc, 'irmc_redfish_get', side_effect=[(200, res, 'OK'), (200, log, 'OK')]):
            status, data, msg = irmc.waitForSessionToFinish(module, 1)

        assert status == 29
        assert data == {'SessionLog': 'detail'}
        assert msg == 'Session result: terminated with error'

    def test_polls_until_terminated(self, module, no_sleep):
        """終了するまでポーリングを続ける"""
        running = response('running')
        done = response('terminated')
        get = Mock(side_effect=[(200, running, 'OK'), (200, running, 'OK'), (200, done, 'OK')])
        with patch.object(irmc, 'irmc_redfish_get', get):
            status, _data, msg = irmc.waitForSessionToFinish(module, 1)

        assert status == 200
        assert msg == 'Session result: terminated'
        assert get.call_count == 3

    def test_http_error_returns_immediately(self, module, no_sleep):
        """HTTP レベルのエラーはリトライせず即座に返す"""
        get = Mock(return_value=(404, 'not found', 'GET request was not successful'))
        with patch.object(irmc, 'irmc_redfish_get', get):
            status, _data, _msg = irmc.waitForSessionToFinish(module, 1)

        assert status == 404
        assert get.call_count == 1


# ========================================
# タイムアウト
# ========================================


class TestWaitForSessionToFinishTimeout:
    """セッションが終わらない場合の打ち切り"""

    def test_returns_status_28_on_timeout(self, module, no_sleep):
        """timeout を超えたら status 28 で抜ける"""
        get = Mock(return_value=(200, response('running'), 'OK'))
        with patch.object(irmc, 'irmc_redfish_get', get):
            status, _data, msg = irmc.waitForSessionToFinish(module, 7, timeout=30)

        assert status == 28
        assert 'Timeout (30s)' in msg
        assert "last status: 'running'" in msg

    def test_timeout_message_points_at_session_log(self, module, no_sleep):
        """タイムアウトのメッセージにセッションログのURLを含める"""
        with patch.object(irmc, 'irmc_redfish_get', return_value=(200, response('running'), 'OK')):
            _status, _data, msg = irmc.waitForSessionToFinish(module, 7, timeout=30)

        assert 'https://192.0.2.1/sessionInformation/7/log' in msg

    def test_does_not_loop_forever(self, module, no_sleep):
        """終わらないセッションでも有限回で抜ける"""
        get = Mock(return_value=(200, response('running'), 'OK'))
        with patch.object(irmc, 'irmc_redfish_get', get):
            irmc.waitForSessionToFinish(module, 1, timeout=100, poll_interval=10)

        assert get.call_count < 100


# ========================================
# 通信エラーのリトライ
# ========================================


class TestWaitForSessionToFinishTransportErrors:
    """一過性の通信エラーへの耐性"""

    def test_recovers_within_error_retries(self, module, no_sleep):
        """error_retries 以内で回復すれば成功する"""
        get = Mock(side_effect=[
            (99, 'traceback', 'GET request encountered exception'),
            (99, 'traceback', 'GET request encountered exception'),
            (200, response('terminated'), 'OK'),
        ])
        with patch.object(irmc, 'irmc_redfish_get', get):
            status, _data, msg = irmc.waitForSessionToFinish(module, 1, error_retries=6)

        assert status == 200
        assert msg == 'Session result: terminated'
        assert get.call_count == 3

    def test_gives_up_after_error_retries(self, module, no_sleep):
        """error_retries を超えたらそのエラーを返す"""
        get = Mock(return_value=(99, 'traceback', 'GET request encountered exception'))
        with patch.object(irmc, 'irmc_redfish_get', get):
            status, _data, msg = irmc.waitForSessionToFinish(module, 1, error_retries=3)

        assert status == 99
        assert msg == 'GET request encountered exception'
        assert get.call_count == 4  # 初回 + リトライ3回

    def test_error_counter_resets_after_success(self, module, no_sleep):
        """成功を挟めば連続エラー数はリセットされる"""
        error = (99, 'traceback', 'GET request encountered exception')
        running = (200, response('running'), 'OK')
        done = (200, response('terminated'), 'OK')
        get = Mock(side_effect=[error, error, running, error, error, done])
        with patch.object(irmc, 'irmc_redfish_get', get):
            status, _data, _msg = irmc.waitForSessionToFinish(module, 1, error_retries=2)

        assert status == 200
        assert get.call_count == 6


# ========================================
# 進捗ログ
# ========================================


class TestWaitForSessionToFinishProgressLog:
    """待機中に別端末から追えるようにするためのログ出力"""

    def test_logs_session_url_when_waiting_starts(self, module, no_sleep):
        """実際に待つことになったらセッションログのURLを出す"""
        get = Mock(side_effect=[(200, response('running'), 'OK'), (200, response('terminated'), 'OK')])
        with patch.object(irmc, 'irmc_redfish_get', get):
            irmc.waitForSessionToFinish(module, 42)

        first = module.log.call_args_list[0][0][0]
        assert 'https://192.0.2.1/sessionInformation/42/log' in first
        assert 'Waiting for session 42' in first

    def test_silent_for_already_terminated_session(self, module, no_sleep):
        """終了済みのセッションでは何も出さない

        waitForIrmcSessionsInactive() が過去のセッション全てに対して呼ぶため、
        待たないセッションまでログに出すと本命のセッションが埋もれる。
        """
        with patch.object(irmc, 'irmc_redfish_get', return_value=(200, response('terminated'), 'OK')):
            irmc.waitForSessionToFinish(module, 42)

        assert module.log.call_count == 0

    def test_announces_only_once(self, module, no_sleep):
        """待機中の URL 出力は1回だけ"""
        get = Mock(return_value=(200, response('running'), 'OK'))
        with patch.object(irmc, 'irmc_redfish_get', get):
            irmc.waitForSessionToFinish(module, 42, timeout=100, log_interval=20)

        announcements = [c[0][0] for c in module.log.call_args_list if 'Waiting for session' in c[0][0]]
        assert len(announcements) == 1

    def test_logs_progress_while_waiting(self, module, no_sleep):
        """log_interval ごとに経過を出す"""
        get = Mock(return_value=(200, response('running'), 'OK'))
        with patch.object(irmc, 'irmc_redfish_get', get):
            irmc.waitForSessionToFinish(module, 1, timeout=100, log_interval=20)

        progress = [c[0][0] for c in module.log.call_args_list if 'still' in c[0][0]]
        assert progress
        assert "Session 1 still 'running'" in progress[0]

    def test_logs_transport_errors(self, module, no_sleep):
        """通信エラーはリトライ回数つきでログに残す"""
        get = Mock(return_value=(99, 'traceback', 'GET request encountered exception'))
        with patch.object(irmc, 'irmc_redfish_get', get):
            irmc.waitForSessionToFinish(module, 1, error_retries=2)

        failures = [c[0][0] for c in module.log.call_args_list if 'request failed' in c[0][0]]
        assert 'Session 1: request failed (1/2)' in failures[0]
