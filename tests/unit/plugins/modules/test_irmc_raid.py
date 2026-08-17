#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmc_raidモジュールのユニットテスト

このテストファイルは、
irmc_raidモジュールの各関数が実機データをどのように処理するかを
明確化するために作成されています。
"""

from unittest.mock import MagicMock
from requests.structures import CaseInsensitiveDict
from ansible_collections.fsas.primergy.plugins.modules.irmc_raid import (
    get_disk,
    get_logicaldrive,
    get_adapter,
    get_raid_configuration
)
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import Response


# ========================================
# Tests
# ========================================

class TestGetDisk:
    """get_disk()関数のユニットテスト

    データソース:
    - API: GET /rest/v1/Oem/eLCM/ProfileManagement/RAIDAdapter
    - JSONパス: Server.HWConfigurationIrmc.Adapters.RAIDAdapter[0].PhysicalDisks.PhysicalDisk[0]

    データフロー:
    1. API レスポンス → irmc_profile (raidadapter_profile変数)
    2. get_raid_configuration() L429: dig(adapter, 'PhysicalDisks', 'PhysicalDisk')
    3. get_raid_configuration() L432 or L444: get_disk(pd) 呼び出し
    """

    def test_get_disk_real_data(self, raidadapter_profile_response):
        """実機データに基づくPhysicalDisk変換テスト

        データフロー:
          1. API: GET /rest/v1/Oem/eLCM/ProfileManagement/RAIDAdapter
             → raidadapter_profile (APIレスポンス全体)

          2. get_raid_configuration() L427-429:
             - adapter = dig(raidadapter_profile, 'Server', 'HWConfigurationIrmc', 'Adapters', 'RAIDAdapter')[0]
             - disk_data = dig(adapter, 'PhysicalDisks', 'PhysicalDisk')
             → PhysicalDisk配列を取得

          3. get_raid_configuration() L432 or L444:
             - for pd in disk_data: disk_list = get_disk(pd)
             → PhysicalDisk配列の各要素をget_disk()に渡す

        期待される変換:
          - @Number ("0") → id (文字列のまま保持)
          - Slot (0) → slot (整数のまま保持)
          - Product ("SAMSUNG MZ7L348") → name
          - Size.#text (447) + Size.@Unit ("GB") → size ("447 GB")

        無視されるフィールド:
          - @Action, PDStatus, Interface, Type, Vendor
        """
        # APIレスポンス全体から該当部分を取り出す
        # get_raid_configuration() L427-429 と同じ抽出処理
        adapter = raidadapter_profile_response['Server']['HWConfigurationIrmc']['Adapters']['RAIDAdapter'][0]
        physical_disk = adapter['PhysicalDisks']['PhysicalDisk'][0]

        # 取り出したデータの確認
        assert physical_disk['@Number'] == '0'
        assert physical_disk['Slot'] == 0
        assert physical_disk['Product'] == 'SAMSUNG MZ7L348'
        assert physical_disk['Size']['#text'] == 447
        assert physical_disk['Size']['@Unit'] == 'GB'

        # get_disk()実行（irmc_raid.py L487-493）
        result = get_disk(physical_disk)

        # 検証: 期待される出力構造
        # get_disk()は以下のフィールドを持つ辞書を返す
        assert result == {
            'id': '0',                    # dig(pd, '@Number') → 文字列"0"
            'slot': 0,                    # dig(pd, 'Slot') → 整数0
            'name': 'SAMSUNG MZ7L348',    # dig(pd, 'Product')
            'size': '447 GB'              # f"{dig(pd, 'Size', '#text')} {dig(pd, 'Size', '@Unit')}"
        }

        # 個別フィールド検証
        assert result['id'] == '0', "@Number は文字列として保持される"
        assert result['slot'] == 0, "Slot は整数として保持される"
        assert result['name'] == 'SAMSUNG MZ7L348', "Product が name に設定される"
        assert result['size'] == '447 GB', "Size.#text と Size.@Unit が結合される"

        # 型の検証
        assert isinstance(result['id'], str), "id は文字列型"
        assert isinstance(result['slot'], int), "slot は整数型"
        assert isinstance(result['name'], str), "name は文字列型"
        assert isinstance(result['size'], str), "size は文字列型"


class TestGetLogicaldrive:
    """get_logicaldrive()関数のユニットテスト

    データソース:
    - API: GET /rest/v1/Oem/eLCM/ProfileManagement/RAIDAdapter
    - JSONパス: Server.HWConfigurationIrmc.Adapters.RAIDAdapter[0].LogicalDrives.LogicalDrive[0]

    データフロー:
    1. API レスポンス → irmc_profile (raidadapter_profile変数)
    2. get_raid_configuration() L430: dig(adapter, 'LogicalDrives', 'LogicalDrive')
    3. get_raid_configuration() L436: get_logicaldrive(ld) 呼び出し
    """

    def test_get_logicaldrive_real_data(self, raidadapter_profile_response):
        """実機データに基づくLogicalDrive変換テスト

        データフロー:
          1. API: GET /rest/v1/Oem/eLCM/ProfileManagement/RAIDAdapter
             → raidadapter_profile (APIレスポンス全体)

          2. get_raid_configuration() L427-430:
             - adapter = dig(raidadapter_profile, 'Server', 'HWConfigurationIrmc', 'Adapters', 'RAIDAdapter')[0]
             - ld_data = dig(adapter, 'LogicalDrives', 'LogicalDrive')
             → LogicalDrive配列を取得

          3. get_raid_configuration() L435-436:
             - if 'Key' not in ld_data:
             -   for ld in ld_data: array_list = get_logicaldrive(ld)
             → LogicalDrive配列の各要素をget_logicaldrive()に渡す

        期待される変換:
          - @Number (239) → id (整数のまま保持)
          - RaidLevel ("0") → level
          - Name ("LogicalDrive_0") → name
          - disks は空リスト [] で初期化（後続処理で追加される）

        無視されるフィールド:
          - @Action, ArrayRefs, WriteMode, ReadMode, CacheMode, DiskCacheMode,
            Stripe, InitMode, LDStatus, Size
        """
        # APIレスポンス全体から該当部分を取り出す
        # get_raid_configuration() L427-430 と同じ抽出処理
        adapter = raidadapter_profile_response['Server']['HWConfigurationIrmc']['Adapters']['RAIDAdapter'][0]
        logical_drive = adapter['LogicalDrives']['LogicalDrive'][0]

        # 取り出したデータの確認
        assert logical_drive['@Number'] == 239
        assert logical_drive['RaidLevel'] == '0'
        assert logical_drive['Name'] == 'LogicalDrive_0'

        # get_logicaldrive()実行（irmc_raid.py L478-484）
        result = get_logicaldrive(logical_drive)

        # 検証: 期待される出力構造
        # get_logicaldrive()は以下のフィールドを持つ辞書を返す
        assert result == {
            'id': 239,                  # dig(ld, '@Number') → 整数239
            'level': '0',               # dig(ld, 'RaidLevel') → 文字列"0"
            'name': 'LogicalDrive_0',   # dig(ld, 'Name')
            'disks': []                 # 空リストで初期化（後続処理で追加）
        }

        # 個別フィールド検証
        assert result['id'] == 239, "@Number は整数として保持される"
        assert result['level'] == '0', "RaidLevel は文字列として保持される"
        assert result['name'] == 'LogicalDrive_0', "Name がそのまま設定される"
        assert result['disks'] == [], "disks は空リストで初期化される"

        # 型の検証
        assert isinstance(result['id'], int), "id は整数型"
        assert isinstance(result['level'], str), "level は文字列型"
        assert isinstance(result['name'], str), "name は文字列型"
        assert isinstance(result['disks'], list), "disks はリスト型"
        assert len(result['disks']) == 0, "disks は空リスト"


class TestGetAdapter:
    """get_adapter()関数のユニットテスト

    データソース:
    - RAIDAdapter情報: GET /rest/v1/Oem/eLCM/ProfileManagement/RAIDAdapter
    - Storage情報: GET /redfish/v1/Systems/0/Storage?$expand=Members

    データフロー:
    1. get_raid_configuration() L426でget_adapter()を呼び出し
    2. get_adapter()は2つのデータソースを使用:
       - adapter引数: RAIDAdapterProfile APIから抽出された1つのRAIDAdapter要素
       - Storage API: irmc.get()で取得するRedfish Storage情報
    """

    def test_get_adapter_real_data(self, raidadapter_profile_response, storage_response):
        """実機データに基づくAdapter情報取得テスト

        使用フィールド（get_adapter() L453-475で参照）:
        - adapter['@AdapterId'] → ctrl['id'], ctrl['name']（初期値）
        - adapter['Features']['RaidLevel'] → ctrl['level']
        - storage_response['Members'][*]['StorageControllers'][*]['MemberId'] → アダプタID照合用
        - マッチしたStorageController['Model'] → ctrl['name']（上書き）
        - マッチしたStorageController['FirmwareVersion'] → ctrl['firmware']
        - マッチしたStorageController['Oem']['ts_fujitsu']['DriveCount'] → ctrl['drives']
        - マッチしたStorageController['Oem']['ts_fujitsu']['VolumeCount'] → ctrl['volumes']

        未使用フィールド例（Storage APIレスポンスの大部分）:
        - StorageControllers[0]['Oem']['ts_fujitsu']['ControllerNumber']
        - StorageControllers[0]['Oem']['ts_fujitsu']['VendorId']
        - StorageControllers[0]['Oem']['ts_fujitsu']['FirmwarePackageVersion']
        - その他300行以上のOEM属性

        注意:
        get_adapter() L469のロジックには潜在的なバグ（？）と想定される仕様があります:
        - '@AdapterId'.replace('RAIDAdapter', '') でIDを抽出（例: 'RAIDAdapter0' → '0'）
        - StorageControllers[*].MemberIdと照合
        - 複数マッチした場合、最後のマッチが使われる（breakが内側ループのみ）

        実機データ（*.*.*.66）では:
        - Storage[0]: PRAID EP640i, StorageControllers[0].MemberId='0'
        - Storage[1]: Windows AHCI, StorageControllers[0].MemberId='0'

        両方がMemberId='0'でマッチするため、最後のStorage[1]（Windows AHCI）が選択されます。
        これは意図した動作ではない可能性がありますが、現状の動作を文書化します。
        """
        # モックの準備
        mock_module = MagicMock()
        mock_irmc = MagicMock()

        # irmc.get()のモック設定
        # get_adapter() L460: irmc.get('redfish/v1/Systems/0/Storage?$expand=Members')
        mock_irmc.get.return_value = Response(
            body=storage_response,
            headers=CaseInsensitiveDict(),
            status=200
        )

        # irmc.vendor属性のモック設定
        # get_adapter() L472-473: dig(sc, 'Oem', irmc.vendor, 'DriveCount')
        mock_irmc.vendor = 'ts_fujitsu'

        # RAIDAdapterProfile APIレスポンスから該当部分を取り出す
        # get_raid_configuration() L426と同じ抽出処理
        adapter = raidadapter_profile_response['Server']['HWConfigurationIrmc']['Adapters']['RAIDAdapter'][0]

        # 入力データの確認
        assert adapter['@AdapterId'] == 'RAIDAdapter0'
        assert adapter['Features']['RaidLevel'] == '0,1,5,6,1E,10,50,60'

        # get_adapter()実行
        result = get_adapter(mock_module, mock_irmc, adapter)

        # irmc.get()が正しいパスで呼ばれたことを確認
        mock_irmc.get.assert_called_once_with('redfish/v1/Systems/0/Storage?$expand=Members')

        # 検証: 実際の出力構造（現状の動作を文書化）
        # 注意: 複数マッチのため、最後のStorage[1]（Windows AHCI）が選択される
        assert result == {
            'id': 'RAIDAdapter0',                           # dig(adapter, '@AdapterId')
            'name': 'Advanced Host Controller Interface',  # Storage[1]のModel（バグ的動作）
            'level': '0,1,5,6,1E,10,50,60',                 # dig(adapter, 'Features', 'RaidLevel')
            'logical_drives': [],                           # 空リストで初期化
            'unused_disks': [],                             # 空リストで初期化
            'firmware': None,                               # Storage[1]のFirmwareVersion（None）
            'drives': 0,                                    # Storage[1]のDriveCount（0）
            'volumes': 0                                    # Storage[1]のVolumeCount（0）
        }

        # 個別フィールド検証
        assert result['id'] == 'RAIDAdapter0', "@AdapterId がそのまま設定される"
        assert result['name'] == 'Advanced Host Controller Interface', "最後にマッチしたStorage[1]のModel"
        assert result['level'] == '0,1,5,6,1E,10,50,60', "サポートRAIDレベルのリスト"
        assert result['firmware'] is None, "Storage[1]にはFirmwareVersionがない"
        assert result['drives'] == 0, "Storage[1]のDriveCountは0"
        assert result['volumes'] == 0, "Storage[1]のVolumeCountは0"
        assert result['logical_drives'] == [], "空リストで初期化（後続処理で追加）"
        assert result['unused_disks'] == [], "空リストで初期化（後続処理で追加）"

        # 型の検証
        assert isinstance(result['id'], str), "id は文字列型"
        assert isinstance(result['name'], str), "name は文字列型"
        assert isinstance(result['level'], str), "level は文字列型（カンマ区切り）"
        assert result['firmware'] is None, "firmware はNone（Storage[1]）"
        assert isinstance(result['drives'], int), "drives は整数型"
        assert isinstance(result['volumes'], int), "volumes は整数型"
        assert isinstance(result['logical_drives'], list), "logical_drives はリスト型"
        assert isinstance(result['unused_disks'], list), "unused_disks はリスト型"


class TestGetRaidConfiguration:
    """get_raid_configuration()関数のユニットテスト

    データソース:
    - RAIDAdapterProfile API: GET /rest/v1/Oem/eLCM/ProfileManagement/RAIDAdapter
    - Storage API: GET /redfish/v1/Systems/0/Storage?$expand=Members

    データフロー:
    1. RAIDAdapterProfile APIレスポンス全体を受け取る
    2. 各RAIDAdapterに対して:
       - get_adapter()でAdapter情報とStorage APIデータを統合
       - PhysicalDisksをすべてunused_disksに追加
       - LogicalDrivesを処理:
         - ArrayRefs → Array → PhysicalDiskRefs → PhysicalDisk の参照チェーンを辿る
         - 使用されているディスクをLogicalDrive.disksに追加
         - 使用されているディスクをunused_disksから削除
    """

    def test_get_raid_configuration_real_data(self, raidadapter_profile_response, storage_response):
        """実機データに基づくRAID構成取得テスト

        ArrayRefs参照チェーン（実機データ）:
        1. LogicalDrive[@Number=239]
        2. → ArrayRef[@Number=0]
        3. → Array[@Number=0]
        4. → PhysicalDiskRef[@Number="0"]
        5. → PhysicalDisk[@Number="0"]（SAMSUNG MZ7L348, 447GB）

        unused_disks管理:
        - L431-433: すべてのPhysicalDisk（1台）を初期状態でunused_disksに追加
        - L434-447: LogicalDrive処理中に:
          - PhysicalDisk[@Number="0"]をLogicalDrive.disksに追加
          - PhysicalDisk[@Number="0"]をunused_disksから削除
        - 結果: unused_disks = []（すべてのディスクが使用済み）
        """
        # モックの準備
        mock_module = MagicMock()
        mock_irmc = MagicMock()

        # irmc.get()のモック設定（get_adapter()内で呼ばれる）
        mock_irmc.get.return_value = Response(
            body=storage_response,
            headers=CaseInsensitiveDict(),
            status=200
        )

        # irmc.vendor属性のモック設定
        mock_irmc.vendor = 'ts_fujitsu'

        # get_raid_configuration()実行
        result = get_raid_configuration(mock_module, mock_irmc, raidadapter_profile_response)

        # 基本構造の検証
        assert isinstance(result, list), "結果はリスト型"
        assert len(result) == 1, "RAIDAdapter 1台"

        # Adapter情報の検証（get_adapter()から取得）
        adapter = result[0]
        assert adapter['id'] == 'RAIDAdapter0'
        assert adapter['name'] == 'Advanced Host Controller Interface'
        assert adapter['level'] == '0,1,5,6,1E,10,50,60'
        assert adapter['firmware'] is None
        assert adapter['drives'] == 0
        assert adapter['volumes'] == 0

        # LogicalDrives検証
        assert len(adapter['logical_drives']) == 1, "LogicalDrive 1個"
        assert adapter['logical_drives'] == [
            {
                'id': 239,
                'level': '0',
                'name': 'LogicalDrive_0',
                'disks': [
                    {
                        'id': '0',
                        'slot': 0,
                        'name': 'SAMSUNG MZ7L348',
                        'size': '447 GB'
                    }
                ]
            }
        ]

        # unused_disks検証（ArrayRefs参照チェーンにより、すべてのディスクが使用済み）
        assert adapter['unused_disks'] == [], "すべてのディスクがLogicalDriveで使用済み"
