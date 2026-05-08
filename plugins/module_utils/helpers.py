# Copyright 2018-2025 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible Collection共通ヘルパー関数

このモジュールは、JSON処理等の汎用的なユーティリティ関数を提供します。
"""

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

from typing import Any


def dig(data: Any, *keys, default=None) -> Any:
    """ネストされた辞書から値を安全に取得します（Ruby's Hash#dig inspired）。

    この関数名はRubyの Hash#dig メソッドから命名されています。

    キーが存在しない場合はdefaultを返しますが、
    キーが存在して値がNoneの場合はNoneを返します。

    引数:
        data - 検索対象の辞書
        *keys - 取得するキーのパス（可変長引数）
        default - キーが存在しない場合のデフォルト値

    戻り値:
        取得した値、キーが存在しない場合はdefault

    使用例:
        >>> data = {'Status': {'State': 'Enabled'}}
        >>> dig(data, 'Status', 'State')
        'Enabled'

        >>> dig(data, 'Status', 'Missing', default='Unknown')
        'Unknown'

        >>> data2 = {'Status': {'State': None}}
        >>> dig(data2, 'Status', 'State', default='Unknown')
        None  # キーは存在するのでNoneを返す

        >>> data3 = {'count': 0, 'flag': False}
        >>> dig(data3, 'count', default=-1)
        0  # Falsy値もそのまま返す

        >>> dig(data3, 'flag', default=True)
        False  # Falsy値もそのまま返す
    """
    result = data
    for key in keys:
        if isinstance(result, dict):
            # キーの存在を明示的にチェック
            if key in result:
                result = result[key]
            else:
                # キーが存在しない場合のみdefaultを返す
                return default
        else:
            # 辞書でない場合は探索不可
            return default

    # ここまで到達した場合、すべてのキーが存在した
    # 値がNoneや0、False等のFalsy値でもそのまま返す
    return result
