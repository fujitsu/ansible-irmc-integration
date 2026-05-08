# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""ログ出力インターフェースとその実装

このモジュールは、AnsibleModuleのログ機能をラップし、テスタビリティを保ちながら
ログ出力を行うためのクラスを提供します。
"""

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

from typing import Protocol, Any, Optional


class Logger(Protocol):
    """ログ出力インターフェース

    このプロトコルは、warn/log/debugの3つのログレベルを定義します。
    AnsibleModuleが持つログ出力機能（warn()/log()/debug()）に対応しています。
    実装クラスはこれらのメソッドを提供する必要があります。
    """

    def warn(self, msg: str) -> None:
        """警告メッセージを出力します。

        引数:
            msg - ログメッセージ
        """
        ...

    def log(self, msg: str) -> None:
        """ログメッセージを出力します。

        引数:
            msg - ログメッセージ
        """
        ...

    def debug(self, msg: str) -> None:
        """デバッグメッセージを出力します。

        引数:
            msg - ログメッセージ
        """
        ...


class AnsibleLogger:
    """AnsibleModule用のLoggerラッパー（ログ蓄積機能付き）

    AnsibleModuleのwarn/log/debugメソッドをラップし、
    Loggerプロトコルを実装します。

    全てのログメッセージは内部バッファに時系列順で蓄積され、
    logsプロパティで取得できます。

    引数:
        module - AnsibleModuleインスタンス
    """

    def __init__(self, module: Any):
        """AnsibleLoggerを初期化します。

        引数:
            module - AnsibleModuleインスタンス
        """
        self.module = module
        self._log_buffer: list[tuple[int, str, str]] = []

    def warn(self, msg: str) -> None:
        """警告メッセージを出力し、バッファに蓄積します。

        引数:
            msg - ログメッセージ
        """
        self.module.warn(msg)
        self._log_buffer.append((1, 'WARN', msg))

    def log(self, msg: str) -> None:
        """ログメッセージを出力し、バッファに蓄積します。

        引数:
            msg - ログメッセージ
        """
        self.module.log(msg)
        self._log_buffer.append((2, 'LOG', msg))

    def debug(self, msg: str) -> None:
        """デバッグメッセージを出力し、バッファに蓄積します。

        引数:
            msg - ログメッセージ
        """
        self.module.debug(msg)
        self._log_buffer.append((3, 'DEBUG', msg))

    def logs(self) -> Optional[list[str]]:
        """蓄積したログをverbosityに応じてフィルタリングして取得します。

        verbosityレベルに応じてフィルタリングされたログを返します：
        - specified_verbosity<=1 (-v): WARN のみ
        - specified_verbosity<=2 (-vv): WARN + LOG
        - specified_verbosity<=3 (-vvv): WARN + LOG + DEBUG

        戻り値:
            フィルタリング済みログメッセージの配列、またはNone
            verbosityレベルが下限値(-v)未満の場合はNone

        使用例:
            logs = logger.logs()
            if logs is not None:
                result['_logs'] = logs
        """
        specified_verbosity = getattr(self.module, '_verbosity', 0)

        if specified_verbosity < 1:
            return None

        # verbosityに応じてフィルタリング
        filtered = []
        for verbosity, level, msg in self._log_buffer:
            if verbosity <= specified_verbosity:
                filtered.append((level, msg))

        # フォーマットして返す
        return [f'[{level}] {msg}' for level, msg in filtered]

    def to_logs_dict(self) -> dict[str, list[str]]:
        """蓄積したログをverbosityに応じてフィルタリングし、
        辞書として返します。

        戻り値:
            ログがある場合は{'_logs': [...]}、ない場合は{}

        使用例:
            result = controller_result.to_exit_dict() | logger.to_logs_dict()
            module.exit_json(**result)
        """
        logs = self.logs()
        return {'_logs': logs} if logs is not None else {}


class MockLogger:
    """テスト用のLoggerモック

    テスト時に使用するためのLoggerモック実装です。
    各ログレベルのメッセージを内部リストに保存します。
    """

    def __init__(self):
        """MockLoggerを初期化します。"""
        self.messages: dict[str, list[str]] = {'warn': [], 'log': [], 'debug': []}

    def warn(self, msg: str) -> None:
        """警告メッセージを記録します。

        引数:
            msg - ログメッセージ
        """
        self.messages['warn'].append(msg)

    def log(self, msg: str) -> None:
        """ログメッセージを記録します。

        引数:
            msg - ログメッセージ
        """
        self.messages['log'].append(msg)

    def debug(self, msg: str) -> None:
        """デバッグメッセージを記録します。

        引数:
            msg - ログメッセージ
        """
        self.messages['debug'].append(msg)
