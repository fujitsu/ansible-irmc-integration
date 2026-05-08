# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""iRMC Redfish APIクライアント

このモジュールは、iRMCのRedfish APIへのアクセスを提供するクライアントクラスを定義します。
"""

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

import json
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Dict, Any, Optional, Tuple, Mapping, TYPE_CHECKING

from ansible_collections.fsas.primergy.plugins.module_utils.irmc_session_information import SessionInformation

# 型チェック時のみインポート（型ヒント専用、起動速度最適化のため）
# LoggerはProtocolで実行時にインスタンス化されないため、mypyなどの型チェッカーでのみ必要
if TYPE_CHECKING:
    from ansible_collections.fsas.primergy.plugins.module_utils.logger import Logger

try:
    import requests
    from requests.auth import HTTPBasicAuth
    from requests.adapters import HTTPAdapter
    from requests.structures import CaseInsensitiveDict
    import urllib3
    from urllib3.util.retry import Retry
    from urllib3.exceptions import InsecureRequestWarning

    urllib3.disable_warnings(InsecureRequestWarning)
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass(frozen=True)
class Request:
    """HTTPリクエスト情報を保持するクラスです。

    このクラスは、HTTPリクエストのメソッドとパスを保持し、
    Responseオブジェクトと関連付けられます。

    引数:
        method - HTTPメソッド（GET, POST, PATCH等）
        path - リクエストパス（例: '/redfish/v1/Systems/0'）
    """

    method: str = ''
    path: str = ''


@dataclass(frozen=True)
class Response:
    """HTTPレスポンスを表すクラスです。

    このクラスは、HTTPレスポンスの内容とリクエスト情報を保持し、
    属性アクセスとタプル展開の両方の方法でアクセス可能にします。

    引数:
        body - レスポンスボディ（dictまたはstr）
        headers - レスポンスヘッダー（CaseInsensitiveDict）
        status - HTTPステータスコード（int）
        request - リクエスト情報（Request、オプション）
    """

    body: Any
    headers: CaseInsensitiveDict[str, str]
    status: int
    request: Request = field(default_factory=Request)

    def __iter__(self):
        """タプル展開を可能にします。

        使用例:
            body, headers, status = response

        注意: requestはタプル展開には含まれません（後方互換性維持）
        """
        return iter((self.body, self.headers, self.status))


def _parse_irmc_version_from_server_header(server_header: Optional[str]) -> Optional[str]:
    """Serverヘッダーの文字列からiRMCバージョンを抽出します。

    この関数はモジュール内部で使用されるプライベート関数です。

    Serverヘッダーの想定フォーマット（大文字・小文字・空白の数の違いは無視）:
        "iRMC S6 Server" → "S6"
        "IRMC S7 SERVER" → "S7"
        "irmc  s10  server" → "S10"

    引数:
        server_header - Serverヘッダーの文字列（Noneも許容）

    戻り値:
        バージョン文字列（例: "S6", "S7", "S10"）、または None

    例外:
        発生しない（すべてのエラーケースでNoneを返す）
    """
    if not server_header:
        return None

    import re
    match = re.search(r'irmc\s+(s\d+)', server_header, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None


class iRMC:
    """iRMCのRedfishインターフェースへのアクセスを提供するクライアントクラスです。

    このクラスは、iRMCのRedfish APIに対してHTTPリクエストを送信し、
    レスポンスをキャッシュする機能を提供します。

    引数:
        ipaddress - iRMCのIPアドレスまたはホスト名
        username - 認証用のユーザー名
        password - 認証用のパスワード
        port - ポート番号（デフォルト: 443）
        validate_certs - SSL証明書の検証を行うか（デフォルト: True）
        logger - ログ出力用のLoggerインスタンス（オプション）
        raise_on_error - エラー時に例外を送出するか（デフォルト: False、既存動作維持）
    """

    def __init__(
        self,
        ipaddress: str,
        username: str,
        password: str,
        port: int = 443,
        validate_certs: bool = True,
        logger: Optional['Logger'] = None,
        raise_on_error: bool = False,
    ):
        """iRMCクライアントを初期化します。

        引数:
            ipaddress - IPアドレスまたはホスト名
            username - ユーザー名
            password - パスワード
            port - ポート番号（デフォルト: 443）
            validate_certs - SSL証明書の検証（デフォルト: True）
            logger - ログ出力用のLoggerインスタンス（オプション）
            raise_on_error - エラー時に例外を送出するか（デフォルト: False）
        """
        if not HAS_REQUESTS:
            raise ImportError("Python 'requests' module is required")

        self.ipaddress = ipaddress
        self.username = username
        self.password = password
        self.port = port
        self.validate_certs = validate_certs
        self.logger = logger
        self.raise_on_error = raise_on_error
        self._cache: Dict[Tuple, Response] = {}
        self._session: Optional[requests.Session] = None

    def _warn(self, message: str):
        """警告メッセージを出力します。

        loggerが設定されている場合にのみログを出力します。
        コンソールに常に表示されます。

        引数:
            message - ログメッセージ
        """
        if self.logger:
            self.logger.warn(message)

    def _log(self, message: str):
        """ログメッセージを出力します。

        loggerが設定されている場合にのみログを出力します。
        syslogに記録されます。

        引数:
            message - ログメッセージ
        """
        if self.logger:
            self.logger.log(message)

    def _debug(self, message: str):
        """デバッグメッセージを出力します。

        loggerが設定されている場合にのみログを出力します。
        -vvv時のみ表示されます。

        引数:
            message - ログメッセージ
        """
        if self.logger:
            self.logger.debug(message)

    def _get_session(self) -> requests.Session:
        """HTTPセッションを取得または作成します。

        戻り値:
            requests.Session - HTTPセッション
        """
        if self._session is None:
            self._session = requests.Session()
            retries = Retry(total=5, backoff_factor=0.1)
            self._session.mount('http://', HTTPAdapter(max_retries=retries))
            self._session.mount('https://', HTTPAdapter(max_retries=retries))
        return self._session

    def _build_url(self, path: str) -> str:
        """完全なURLを構築します。

        引数:
            path - リクエストパス

        戻り値:
            str - 完全なURL（https://ipaddress:port/path形式）
        """
        # パスを正規化（'/foo/bar'形式になる）
        normalized = self._normalize_path(path)
        # normalizedは '/foo/bar' 形式なので、そのまま結合
        return f'https://{self.ipaddress}:{self.port}{normalized}'

    def _normalize_path(self, path: str) -> str:
        """パスを正規化します。

        先頭にスラッシュを追加し、末尾のスラッシュを除去します。

        引数:
            path - リクエストパス

        戻り値:
            str - 正規化されたパス（'/foo/bar'形式）
        """
        # 先頭と末尾のスラッシュを除去
        normalized = path.strip('/')
        # 先頭にスラッシュを追加
        return f'/{normalized}'

    def _make_cache_key(
        self, path: str, headers: Optional[Mapping[str, str]]
    ) -> Optional[Tuple]:
        """キャッシュキーを生成します。

        クエリパラメータが含まれている場合はNoneを返します（キャッシュしない）。

        引数:
            path - リクエストパス
            headers - ヘッダー（dict, CaseInsensitiveDict等、任意のMapping）

        戻り値:
            tuple または None - キャッシュキー、またはキャッシュしない場合はNone
        """
        # パスの正規化
        normalized_path = self._normalize_path(path)

        # クエリパラメータがある場合はキャッシュしない
        if '?' in normalized_path:
            return None

        # ヘッダーを含めたキーの生成
        headers_key = frozenset(headers.items()) if headers else frozenset()
        return (normalized_path, headers_key)

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Any] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Response:
        """HTTPリクエストを送信します。

        引数:
            method - HTTPメソッド（GET, POST等）
            path - リクエストパス
            body - リクエストボディ（オプション）
            headers - カスタムヘッダー（dict, CaseInsensitiveDict等、任意のMapping）

        戻り値:
            Response - レスポンスオブジェクト
        """
        # パスを正規化（以降はこの正規化されたpathを使用）
        path = self._normalize_path(path)

        url = self._build_url(path)
        session = self._get_session()

        # リクエスト開始ログ
        start_time = time.time()
        self._debug(f'iRMC Request: {method} {path}')

        # デフォルトヘッダーを設定
        request_headers = CaseInsensitiveDict({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        # bodyを適切な形式に変換し、必要に応じてヘッダーを上書き
        data = None
        if body is not None:
            # マルチパートボディ
            if hasattr(body, 'content_type') and hasattr(body, 'to_string'):
                data = body
                request_headers['Content-Type'] = body.content_type
                # Accept は application/json （iRMCの仕様に準ずる）
                request_headers['Accept'] = 'application/json'

            # XML文字列
            elif isinstance(body, str) and body.strip().startswith('<?xml'):
                data = body
                request_headers['Content-Type'] = 'application/xml'
                request_headers['Accept'] = 'application/xml'

            # 普通のstr/bytes
            elif isinstance(body, (str, bytes)):
                data = body

            # dict/list → JSON化
            else:
                data = json.dumps(body)

        # ユーザー指定のヘッダで上書き
        if headers:
            request_headers.update(headers)

        try:
            response = session.request(
                method=method,
                url=url,
                headers=request_headers,
                data=data,
                auth=HTTPBasicAuth(self.username, self.password),
                verify=self.validate_certs,
            )
            response.connection.close()

            # レスポンスボディの解析
            response_body = None
            if response.text:
                try:
                    response_body = response.json()
                except (json.JSONDecodeError, ValueError):
                    response_body = response.text

            # リクエスト完了ログ
            elapsed_time = time.time() - start_time
            self._debug(
                f'iRMC Response: {method} {path} -> '
                f'Status: {response.status_code}, '
                f'Time: {elapsed_time:.3f}s'
            )

            return Response(
                body=response_body,
                headers=CaseInsensitiveDict(response.headers),
                status=response.status_code,
                request=Request(method, path),
            )

        except Exception as e:
            # エラーログ
            elapsed_time = time.time() - start_time
            self._warn(
                f'iRMC Request Error: {method} {path} -> '
                f'Error: {str(e)}, Time: {elapsed_time:.3f}s'
            )
            # raise_on_errorがTrueの場合は例外を再送出
            if self.raise_on_error:
                raise
            # エラー時もResponseオブジェクトを返す（irmc.py::irmc_redfish_get()との互換性維持）
            return Response(
                body=str(e),
                headers=CaseInsensitiveDict(),
                status=99,
                request=Request(method, path),
            )

    def get(
        self,
        path: str,
        headers: Optional[Mapping[str, str]] = None,
        use_cache: bool = True,
    ) -> Response:
        """GETリクエストを実行します。

        キャッシュ動作:
            - path末尾の/は正規化される（/redfish/v1と/redfish/v1/は同一）
            - クエリパラメータがある場合はキャッシュされない
            - pathとheadersの組み合わせでキャッシュキーを生成

        引数:
            path - リクエスト先のパス（例: "/redfish/v1"）
            headers - 追加するHTTPヘッダー（dict, CaseInsensitiveDict等、任意のMapping）
            use_cache - キャッシュを使用するか（デフォルト: True）

        戻り値:
            Response - レスポンスオブジェクト
        """
        # pathを正規化（以降は正規化されたpathを使用）
        normalized_path = self._normalize_path(path)

        # キャッシュキーの生成
        cache_key = None
        if use_cache:
            cache_key = self._make_cache_key(normalized_path, headers)

        # キャッシュから取得
        if cache_key is not None and cache_key in self._cache:
            self._debug(f'iRMC Cache Hit: GET {normalized_path}')
            return self._cache[cache_key]

        # リクエスト送信
        response = self._request('GET', normalized_path, headers=headers)

        # 成功時（200）のみキャッシュに保存
        if cache_key is not None and response.status == HTTPStatus.OK:
            self._cache[cache_key] = response

        return response

    def post(
        self, path: str, body: Any, headers: Optional[Mapping[str, str]] = None
    ) -> Response:
        """POSTリクエストを実行します。

        引数:
            path - リクエスト先のパス
            body - 送信するデータ（dictまたはJSON文字列）
            headers - 追加するHTTPヘッダー（dict, CaseInsensitiveDict等、任意のMapping）

        戻り値:
            Response - レスポンスオブジェクト
        """
        return self._request('POST', path, body=body, headers=headers)

    def put(
        self, path: str, body: Any, headers: Optional[Mapping[str, str]] = None
    ) -> Response:
        """PUTリクエストを実行します。

        引数:
            path - リクエスト先のパス
            body - 送信するデータ（dictまたはJSON文字列）
            headers - 追加するHTTPヘッダー（dict, CaseInsensitiveDict等、任意のMapping）

        戻り値:
            Response - レスポンスオブジェクト
        """
        return self._request('PUT', path, body=body, headers=headers)

    def patch(
        self, path: str, body: Any, headers: Optional[Mapping[str, str]] = None
    ) -> Response:
        """PATCHリクエストを実行します。

        引数:
            path - リクエスト先のパス
            body - 送信するデータ（dictまたはJSON文字列）
            headers - 追加するHTTPヘッダー（dict, CaseInsensitiveDict等、任意のMapping）

        戻り値:
            Response - レスポンスオブジェクト
        """
        return self._request('PATCH', path, body=body, headers=headers)

    def delete(
        self, path: str, headers: Optional[Mapping[str, str]] = None
    ) -> Response:
        """DELETEリクエストを実行します。

        引数:
            path - リクエスト先のパス
            headers - 追加するHTTPヘッダー（dict, CaseInsensitiveDict等、任意のMapping）

        戻り値:
            Response - レスポンスオブジェクト
        """
        return self._request('DELETE', path, headers=headers)

    def head(
        self, path: str, headers: Optional[Mapping[str, str]] = None
    ) -> Response:
        """HEADリクエストを実行します。

        引数:
            path - リクエスト先のパス
            headers - 追加するHTTPヘッダー（dict, CaseInsensitiveDict等、任意のMapping）

        戻り値:
            Response - レスポンスオブジェクト
        """
        return self._request('HEAD', path, headers=headers)

    def options(
        self, path: str, headers: Optional[Mapping[str, str]] = None
    ) -> Response:
        """OPTIONSリクエストを実行します。

        引数:
            path - リクエスト先のパス
            headers - 追加するHTTPヘッダー（dict, CaseInsensitiveDict等、任意のMapping）

        戻り値:
            Response - レスポンスオブジェクト
        """
        return self._request('OPTIONS', path, headers=headers)

    @property
    def vendor(self) -> Optional[str]:
        """iRMCのベンダー識別子を取得します。

        /redfish/v1をGETしてVendor属性を取得します。
        iRMC S5ではVendor属性が存在しないため、その場合は"ts_fujitsu"にフォールバックします。
        成功時（200）はget()のキャッシュ機構により、2回目以降は再GETされません。
        エラー時は次回アクセス時に再試行されます。

        戻り値:
            str - ベンダー識別子（"ts_fujitsu"、"Fsas"など）
            None - /redfish/v1の取得に失敗した場合

        挙動:
            - 成功時（status=200）かつVendor属性あり: Vendor属性を返す
            - 成功時（status=200）かつVendor属性なし/空: "ts_fujitsu"を返す（S5想定、WARNログ出力）
            - エラー時（status!=200）: Noneを返し、レスポンスはキャッシュされない（次回再試行）
        """
        response = self.get('/redfish/v1')

        if response.status == HTTPStatus.OK and isinstance(response.body, dict):
            vendor = response.body.get('Vendor')

            fallback_value = 'ts_fujitsu'

            # Vendorが無い、または空文字列の場合はts_fujitsuにフォールバック
            if not vendor:  # None or empty string
                self._warn(
                    'iRMC Vendor attribute not found or empty in /redfish/v1, '
                    f'falling back to {fallback_value!r} (assuming S5 or earlier)'
                )
                vendor = fallback_value

            return vendor

        self._warn(
            f'iRMC Vendor detection failed (status={response.status}), '
            'will retry on next access.'
        )
        return None

    @property
    def oem_prefix(self) -> Optional[str]:
        """OEMスキーマ・アクション・パラメータ用のプレフィックスを取得します。

        vendorプロパティの値に基づいて、スキーマ名やアクション名で使用される
        プレフィックスを返します。

        戻り値:
            str - プレフィックス文字列（"FTS" または "Fsas"）
            None - vendorが取得できない場合

        使用例:
            # アクション名の構築
            action = f'#{client.oem_prefix}ComputerSystem.Reset'
            # M7: #FTSComputerSystem.Reset
            # M8: #FsasComputerSystem.Reset

            # スキーマのパース
            if f'#{client.oem_prefix}' in response['@odata.type']:
                # OEMデータの処理
        """
        vendor = self.vendor
        if vendor == 'ts_fujitsu':
            return 'FTS'
        if vendor == 'Fsas':
            return 'Fsas'
        return None

    @property
    def version(self) -> Optional[str]:
        """iRMCサーバーのバージョンを取得します。

        GET /redfish/v1のレスポンスヘッダーから'Server'フィールドを解析し、
        iRMCサーバーのバージョン（例: "S7"）を抽出します。
        成功時（200）はget()のキャッシュ機構により、2回目以降は再GETされません。
        エラー時は次回アクセス時に再試行されます。

        Serverヘッダーの想定フォーマット（大文字・小文字・空白の数の違いは無視、"S{数字}"）:
            "iRMC S7 Server" → "S7"
            "IRMC S8 SERVER" → "S8"
            "irmc  s10" → "S10"

        戻り値:
            str - バージョン文字列（例: "S8"）
            None - Serverヘッダーが存在しない、パターンが一致しない、または取得に失敗した場合

        挙動:
            - 成功時（status=200）: バージョン文字列を返し、レスポンスはキャッシュされる
            - Serverヘッダーが存在しない、またはパターンが一致しない場合: Noneを返すが、レスポンスはキャッシュされる
            - エラー時（status!=200）: Noneを返し、レスポンスはキャッシュされない（次回再試行）
        """
        response = self.get('/redfish/v1')

        if response.status == HTTPStatus.OK:
            # CaseInsensitiveDictなので大文字小文字を気にせずアクセス可能
            server_header = response.headers.get('Server')
            version = _parse_irmc_version_from_server_header(server_header)

            if version:
                self._debug(f'iRMC Server Version detected: {version}')
            else:
                if server_header:
                    self._debug(f'iRMC Server Version pattern not found in Server header: {server_header}')
                else:
                    self._debug('Server header not found in /redfish/v1 response')

            return version

        self._warn(
            f'iRMC Server Version detection failed (status={response.status}), '
            'will retry on next access.'
        )
        return None

    @property
    def sessions(self) -> SessionInformation:
        """sessionInformation APIを操作するSessionInformationインスタンスを取得します。

        このプロパティは、iRMCのsessionInformation APIにアクセスするための
        SessionInformationオブジェクトを返します。初回アクセス時にインスタンスが
        作成され、以降は同じインスタンスが再利用されます。

        戻り値:
            SessionInformation - sessionInformation API操作クラスのインスタンス

        使用例:
            # セッションIDを指定して待機
            session = irmc.sessions.get(session_id)
            result = session.wait_for_finish()

            # セッション一覧を取得
            for session in irmc.sessions.list():
                status = session.get_status()
        """
        if not hasattr(self, '_sessions'):
            self._sessions = SessionInformation(self)
        return self._sessions
