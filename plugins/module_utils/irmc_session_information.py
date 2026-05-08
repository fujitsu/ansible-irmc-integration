# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""iRMC SessionInformation API のラッパークラス

このモジュールは、iRMCのsessionInformation APIを操作するためのクラスを提供します。
"""

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

import time
from typing import TYPE_CHECKING, Optional

from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig

# typing.TYPE_CHECKINGは型チェックのときだけTrueになる
# （循環インポート回避のため）型チェック時のみインポートされる
if TYPE_CHECKING:
    from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC, Response


class Session:
    """個別セッションを操作するクラス

    sessionInformationエンドポイントの特定セッションに対する操作を提供します。
    """

    def __init__(self, irmc: 'iRMC', session_id: int):
        """Sessionクラスを初期化します。

        引数:
            irmc - iRMCクライアントインスタンス
            session_id - セッションID
        """
        self._irmc = irmc
        self._session_id = session_id

    @property
    def id(self) -> int:
        """セッションIDを取得します。

        戻り値:
            セッションID
        """
        return self._session_id

    def get_status(self) -> 'Response':
        """セッションのステータスを取得します。

        sessionInformation/{id}/status にGETリクエストを送信します。

        戻り値:
            Response - iRMCクラスのResponseオブジェクト
        """
        return self._irmc.get(f'sessionInformation/{self._session_id}/status', use_cache=False)

    def get_log(self) -> 'Response':
        """セッションのログを取得します。

        sessionInformation/{id}/log にGETリクエストを送信します。

        戻り値:
            Response - iRMCクラスのResponseオブジェクト
        """
        return self._irmc.get(f'sessionInformation/{self._session_id}/log', use_cache=False)

    def wait_for_finish(self, interval: int = 10, timeout: Optional[int] = None) -> 'Response':
        """セッションが終了するまでポーリングして待機します。

        セッションステータスを定期的に確認し、終了するまで待機します。
        エラーで終了した場合は、自動的にログを取得して返します。

        引数:
            interval - ポーリング間隔（秒）
            timeout - タイムアウト（秒、Noneの場合は無制限）

        戻り値:
            Response - iRMCクラスのResponseオブジェクト
                       正常終了時: statusレスポンス
                       エラー終了時: logレスポンス
        """
        start_time = time.time() if timeout else None

        while True:
            # ステータスを取得
            response = self.get_status()
            if response.status != 200:
                return response

            # セッションステータスを確認
            session_status = dig(response.body, 'Session', 'Status')
            if not session_status:
                # Session.Statusが取得できない場合はエラー
                return response

            # 終了判定
            if 'terminated' in session_status:
                # エラーで終了した場合はログを取得
                if 'error' in session_status:
                    # 循環インポート回避のため、ここでインポート
                    from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import Response
                    body, header, _status = self.get_log()
                    return Response(body, header, 29)  # status=29はirmc.py::waitForFinish()と同じ挙動
                else:
                    # 正常終了
                    return response

            # タイムアウトチェック
            if timeout and start_time:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    # タイムアウトは元のレスポンスを返す
                    return response

            # 待機
            time.sleep(interval)

    def terminate(self) -> 'Response':
        """セッションを終了します。

        sessionInformation/{id}/terminate にDELETEリクエストを送信します。

        戻り値:
            Response - iRMCクラスのResponseオブジェクト
        """
        return self._irmc.delete(f'sessionInformation/{self._session_id}/terminate')

    def remove(self) -> 'Response':
        """セッションを削除します。

        sessionInformation/{id}/remove にDELETEリクエストを送信します。

        戻り値:
            Response - iRMCクラスのResponseオブジェクト
        """
        return self._irmc.delete(f'sessionInformation/{self._session_id}/remove')


class SessionInformation:
    """sessionInformation API全体を操作するクラス

    sessionInformationエンドポイントの全体操作を提供します。
    """

    def __init__(self, irmc: 'iRMC'):
        """SessionInformationクラスを初期化します。

        引数:
            irmc - iRMCクライアントインスタンス
        """
        self._irmc = irmc

    def list(self) -> list['Session']:
        """セッション一覧を取得します（未実装）。

        このメソッドは現在未実装です。
        将来的にsessionInformation にGETリクエストを送信し、
        Sessionオブジェクトのリストを返す予定です。

        例外:
            NotImplementedError - このメソッドは未実装です
        """
        raise NotImplementedError('SessionInformation.list() is not implemented yet')

    def get(self, session_id: int) -> 'Session':
        """指定されたIDのSessionオブジェクトを返します。

        引数:
            session_id - セッションID

        戻り値:
            Sessionオブジェクト
        """
        return Session(self._irmc, session_id)
