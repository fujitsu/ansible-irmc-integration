# 手動テストランナー

> **これはコレクションのメンテナ向けのツールです。**
> リリース前に全モジュールを実機で一括テストし、その結果をエビデンスとして残すために使っています。
>
> **コレクションを利用するだけの方や、コントリビューターの方が実行する必要はありません。**
> 実機の PRIMERGY サーバと、そこへ到達できる `inventory.ini` が必要で、
> ケースによっては電源操作・RAID アレイの削除・ファームウェアの書き換えを伴います。

実機の iRMC に対して `examples/modules/` 配下のサンプルプレイブックを実行し、
その出力を `tests/manual/results/<module>/<name>.txt` にエビデンスとして残すためのツールです。

このランナーは実行結果の**内容**を自動判定しません。`expect_recap`（後述）による
PLAY RECAP の件数チェックだけを行い、設定値が期待通りかどうかは記録されたファイルを人が読んで判断します。

## 事前準備

環境固有のファイルはGitリポジトリに入れていないので、`git clone` 後に用意します。

| 用意するもの    | 方法                                                            |
| --------------- | --------------------------------------------------------------- |
| `inventory.ini` | ルートに作成（「inventory に設定する変数」を参照）              |
| 証明書          | `cd tests/manual/assets/certs && make`（数秒）                  |
| ファームウェア  | ベンダーサイトから入手し `tests/manual/assets/firmware/` へ配置 |

証明書とファームウェアは、それぞれ `irmc_certificate` と `irmc_fwbios_update` の
ケースでのみ必要です。他のケースだけ実行するなら不要です。

## 実行

```bash
# 全ケースを実行
uv run ./tests/manual/run_tests.py

# ケース定義ファイルを指定する（≒ モジュールで選ぶ）
uv run ./tests/manual/run_tests.py --cases tests/manual/cases/irmc_idled.yml

# ケース名で絞り込む（ファイルをまたいで効く）
uv run ./tests/manual/run_tests.py --name get

# 対象ホストを絞り込む
uv run ./tests/manual/run_tests.py --limit 192.0.2.12

# 組み合わせ: irmc_idled の set だけを 192.0.2.12 に対して実行
uv run ./tests/manual/run_tests.py \
  --cases tests/manual/cases/irmc_idled.yml --name set --limit 192.0.2.12
```

### 3つの絞り込み軸

絞り込みは軸ごとに1つのオプションが担当します。

| 軸                       | オプション | 説明                                               |
| ------------------------ | ---------- | -------------------------------------------------- |
| どのファイルを読むか     | `--cases`  | ケース定義ファイルまたはディレクトリ（複数指定可） |
| どのケースを実行するか   | `--name`   | 読み込んだケースを `name` の部分一致で絞り込む     |
| どのホストを対象にするか | `--limit`  | `ansible-playbook --limit` にそのまま渡す          |

`--cases` と `--name` は2段階のパイプラインです。1つのケース定義ファイルには
**複数のケース**が入っている（例: `irmc_idled.yml` には `get` と `set`）ので、
ファイルを選んでから、その中のケースを選ぶ、という順に効きます。

```text
--cases  →  YAMLファイルを読み込む      （既定: tests/manual/cases/ 配下すべて）
             ↓
--name   →  読み込んだケースを絞り込む   （name への部分一致)
             ↓
--limit  →  各プレイブック実行の対象ホストを絞る
```

`--name` は `name` だけを見ます。モジュール単位の選択は `--cases` の担当なので、
`--name irmc_idled` は何にも一致しません。

`--limit` の指定先が inventory に無いと `ansible-playbook` は0ホストで正常終了し
PLAY RECAP を出しません。`expect_recap` のあるステップならランナーが検出し、
`limit '<値>' に一致するホストが inventory にあるか確認してください` を出して失敗させます。

**`--limit` を省略すると全ホストが対象になります。** `host_vars`（後述）があれば動作は正しいのですが、
`irmc_biosbootorder/set` のように再起動を伴うケースは台数分の時間がかかります。

### 全オプション

| オプション       | 既定値                  | 説明                                                     |
| ---------------- | ----------------------- | -------------------------------------------------------- |
| `-c` / `--cases` | `tests/manual/cases/`   | ケース定義ファイルまたはディレクトリ（複数指定可）       |
| `--name`         | なし                    | `name` に部分一致するケースのみ実行                      |
| `--limit`        | なし                    | 対象ホストを絞り込む（`ansible-playbook` への素通し）    |
| `--inventory`    | `inventory.ini`         | インベントリファイル（`ansible-playbook` への素通し）    |
| `--columns`      | `120`                   | エビデンスの横幅（後述）                                 |
| `--playbook-dir` | `examples/modules/`     | ファイル名のみで指定されたプレイブックの基準ディレクトリ |
| `--results-dir`  | `tests/manual/results/` | 結果ファイルの出力先                                     |

## ケース定義スキーマ

1つのテストケースは**名前付きステップ（プレイブック実行）の列**です。
set 本体も、その前処理も、後の状態確認も、電源状態を揃える処理も、すべて同じ形のステップとして書きます。

```yaml
- module: irmc_idled                     # 任意: 出力先 results/<module>/
  name: set                              # 必須: 結果ファイル名 <name>.txt
  playbook: irmc_idled_examples.yml      # 任意: 各ステップの既定プレイブック
  steps:                                 # 必須: 上から順に実行する
    - name: arrange                      # 必須: ログ上のラベル（自由記述）
      description: ID LEDを消灯し、act が必ず変更を伴うようにする   # 任意
      tag: set                           # 任意: --tags。省略時は --tags を付けない
      vars: {state: "Off"}               # 任意: --extra-vars
    - name: before
      tag: get
    - name: act
      tag: set
      vars: {state: "Blinking"}
      expect_recap: {changed: 1, failed: 0}   # 任意: PLAY RECAP の期待値
    - name: after
      tag: get
```

### ケースのキー

| キー       | 必須 | 説明                                                                              |
| ---------- | ---- | --------------------------------------------------------------------------------- |
| `module`   | △    | 出力先 `results/<module>/`。省略時は `playbook` から末尾の `_examples` を除いた値 |
| `name`     | ○    | 結果ファイル名 `<name>.txt`                                                       |
| `playbook` | △    | 各ステップの既定プレイブック。全ステップが自前で `playbook` を持つなら省略可      |
| `steps`    | ○    | ステップ定義のリスト（1件以上）                                                   |

### ステップのキー

| キー                | 必須 | 説明                                                                |
| ------------------- | ---- | ------------------------------------------------------------------- |
| `name`              | ○    | ログ上のラベル。自由記述で、同じ名前を複数回使ってよい              |
| `description`       |      | 見出しに書く補足説明                                                |
| `playbook`          |      | このステップだけプレイブックを差し替える                            |
| `tag`               |      | `--tags` に渡す値。省略すると `--tags` を付けずに実行する           |
| `vars`              |      | `--extra-vars` として渡す変数の辞書                                 |
| `expect_recap`      |      | PLAY RECAP の期待値（後述）                                         |
| `continue_on_error` |      | `true` なら失敗しても後続ステップを実行する（ケース自体は失敗扱い） |

`playbook` はケース単位が既定値、ステップ単位が上書きです。
対象ホストはケース定義には書きません（実行時の `--limit` で指定します）。

### プレイブックのパス解決

- `/` を含む → リポジトリルートからの相対パス（例 `tests/manual/playbooks/ensure_power_state.yml`）
- 含まない → `--playbook-dir`（既定 `examples/modules/`）からの相対パス

### ステップ名の推奨命名

`name` は自由記述ですが、README では以下を推奨します。補足を付けて `arrange (power off)` のように書いても構いません。

| 名前      | 役割                                                                                     |
| --------- | ---------------------------------------------------------------------------------------- |
| `arrange` | 前提を整える。冪等スキップを避けるため act とは別の値へ先に設定する、電源状態を揃える 等 |
| `before`  | 変更前の状態を取得して記録する（get）                                                    |
| `act`     | テスト対象の実行（set）                                                                  |
| `settle`  | act の影響が落ち着くまで待つ。after の get が遷移中の値を拾うのを防ぐ                    |
| `after`   | 変更後の状態を取得して記録する（get）                                                    |

## `expect_recap`

`ansible-playbook` が最後に出力する PLAY RECAP を解析し、期待値と突き合わせます。

```text
PLAY RECAP *********************************************************
192.0.2.10               : ok=1 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
```

- **記述しなければチェックしません**
- 記述したキーだけを見ます（`{changed: 1, failed: 0}` なら `ok` や `skipped` は無視）
- PLAY RECAP に現れる**全ホスト**が期待値と一致することを求めます
- 一致しなければそのステップを失敗として扱い、ランナーは exit code 1 で終了します
- PLAY RECAP が1行も取れなかった場合も失敗とします

### 冪等スキップの検出に使う

一部のモジュールは現在値と要求値が同じとき `skipped` を返します
（`irmc_idled` / `irmc_powerstate` / `irmc_biosbootorder`）。
そのため同じケースを繰り返すと2回目以降が必ず `skipped` になり、エビデンスとして意味をなしません。

これを避けるため、`act` の前に `arrange` で**別の値**を設定しておき、
`act` に `expect_recap: {changed: 1, skipped: 0}` を書いて確実に変更が起きたことを検出します。

### 失敗することを検証する

`failed` または `unreachable` に **1 以上**を書くと、そのステップは
`ansible-playbook` が**非0で終了することを期待している**扱いになります。
専用のキーは用意していません。意図の記述箇所を1つに保ち、期待する統計値と食い違わないようにするためです。

```yaml
    - name: act
      description: 無効なキーの適用を試み、iRMC が拒否することを確認する
      tag: set
      vars: {license_key: "ABDC-EFGH-IJKL-MNOP-QRST-UVWX-YZ"}
      expect_recap: {failed: 1, changed: 0}
```

| 実際の結果               | ステップの判定                                                           |
| ------------------------ | ------------------------------------------------------------------------ |
| 期待どおり失敗した       | OK                                                                       |
| **正常終了してしまった** | NG（`失敗を期待するステップですが ansible-playbook が正常終了しました`） |

**危険な側が失敗として現れる向きに書いてください。** 上の例なら、無効なはずのキーが受理されると
`changed=1` になり NG になります。`changed: 0` を併記しているのはその安全弁です。

`{failed: 0}` を書いた場合や `expect_recap` 自体が無い場合は、従来どおり正常終了を期待します。

## 失敗時の挙動

ステップが失敗（期待と異なる終了コード、または `expect_recap` 不一致）すると、
そのケースはそこで中断され次のケースへ進みます。前提が崩れた状態で後続を走らせてもエビデンスにならないためです。
ステップに `continue_on_error: true` を書けば失敗しても後続を実行します。

「失敗を期待するステップ」が期待どおり失敗した場合は成功扱いなので、ケースは中断されず
`after` まで流れます。

## 電源状態を揃える

`irmc_biosbootorder` の `set` / `default` などは、サーバの電源がオフでないと実行できません。

電源制御も専用の仕組みではなく、単にプレイブックを差し替えたステップとして書きます。

```yaml
    - name: arrange (power off)
      playbook: tests/manual/playbooks/ensure_power_state.yml
      vars: {desired_power_state: "Off"}
```

`tests/manual/playbooks/ensure_power_state.yml` は `hosts: iRMC_group` なので、
インベントリに登録された**全ホスト**へ自動的に適用されます。
`desired_power_state`（`Off` または `On`）が唯一の入力で、その状態に落ち着くまでポーリングして待ちます。

待ち時間は `host_vars/<host>.yml` で機体別に延ばせます。

| 変数                    | 既定値 | 説明                                                   |
| ----------------------- | ------ | ------------------------------------------------------ |
| `power_wait_retries`    | 30     | 電源状態が落ち着くまでのポーリング回数                 |
| `power_wait_delay`      | 10     | ポーリング間隔（秒）                                   |
| `power_request_retries` | 5      | 電源変更要求が iRMC 未応答で失敗したときのリトライ回数 |
| `power_request_delay`   | 10     | 同リトライの間隔（秒）                                 |

もう1つ `power_settle_seconds`（既定 0）があり、電源状態が確定した**後**にさらに待ちます。
iRMC が `Off` を返しても直前まで通電していた場合は内部状態が残っていることがあり、
その状態で RAID 操作を始めると失敗するためです（`irmc_raid` で実測。詳細は
`tests/manual/cases/irmc_raid.yml` の冒頭コメント）。

```yaml
    - name: arrange (power off)
      playbook: tests/manual/playbooks/ensure_power_state.yml
      vars: {desired_power_state: "Off", power_settle_seconds: 60}
```

**これだけは `host_vars` で上書きできません。** 機体差ではなくケース側の要求なので
ケース定義の `vars` から渡し、`--extra-vars` になるためです。`pause` が
`BYPASS_HOST_LOOP` で play に1回しか実行されないことも理由です。
機体ごとに変えたい場合はケース定義の値を直接編集してください。

## イベントログを生成する

`irmc_eventlog` の `clear` は「消える前」と「消えた後」の差がエビデンスになりますが、
**SystemEventLog は空になりうる**ため前提を作る必要があります。
`clear` を実行すると SEL は完全に空になり、`get` の対象も無くなります。

```yaml
    - name: arrange
      playbook: tests/manual/playbooks/send_test_alert.yml
```

`tests/manual/playbooks/send_test_alert.yml` は iRMC の OEM アクション
`FTSComputerSystem.SendTestAlert` を叩いて SEL にエントリを1件生成します。
`Severity: OK` / `Message: Test alert informational` が記録されます。

| 変数                  | 既定値                           | 説明                                                              |
| --------------------- | -------------------------------- | ----------------------------------------------------------------- |
| `test_alert_severity` | `TestAlertSeverityInformational` | `TestAlertSeverityCritical` / `Major` / `Minor` / `Informational` |

**副作用として、iRMC に設定されたアラート通知（メール・SNMP トラップ等）が実際に送信されます。**

このアクションを扱うモジュールはコレクションに無いため、このプレイブックだけは
`ansible.builtin.uri` で Redfish を直接叩いています。

電源操作でも SEL は生成されますが、機種や搭載部品に依存する（非認証メモリの警告など）ため前提としては使えません。

## 所要時間の目安

`irmc_biosbootorder` のケースは**数分から十数分かかります。止まって見えても待ってください。**

BIOS の起動時間は機種によって大きく違います（実測）。

| 機種      | BIOS 起動時間 |
| --------- | ------------- |
| RX1330 M6 | 1:40          |
| TX1320 M6 | 1:50          |
| RX1440 M2 | 3:50          |
| RX2450 M2 | 5:00          |

さらに `force_new: true` でのブート順取得は、iRMC がサーバを graceful shutdown させてから
BIOS パラメータをバックアップし直すため、RX2450 M2 で**実測7分38秒**かかりました。

```text
07:02:28  RetrieveBIOSParameters: Perform graceful shutdown
07:10:02  RetrieveBIOSParameters: BIOS parameter BACKUP successful
07:10:06  TerminateSession
```

`set` / `default` ケースは `before` と `after` で get を2回行うため、
RX2450 M2 では1ケースで15分を超えます。急ぐときは `--limit` で起動の速い機体を選んでください。

### `force_new: false` で短縮してはいけない

`force_new: false` にすればプロファイルの再生成を回避できますが、**エビデンスが無意味になります**。

iRMC が `rest/v1/Oem/eLCM/ProfileManagement/BiosBootOrder` に保持するプロファイルは
`set` でも `default` でも更新されず、`force_new` による再生成でしか実態に追従しません。
`false` だと過去のスナップショットが返ります。

実機（RX2450 M2）で確認した症状です。

| 位置 | `before` / `after`（`force_new: false`） | 直後の get（`force_new: true`） |
| ---- | ---------------------------------------- | ------------------------------- |
| 1    | `NIC.LOM.0.1.IPv4PXE`                    | **`NIC.LOM.0.1.IPv6PXE`**       |
| 2    | `Storage.InternalUSB.0.2.1`              | `NIC.LOM.0.1.IPv4PXE`           |
| 3    | `NIC.LOM.0.1.IPv6PXE`                    | `Storage.InternalUSB.0.2.1`     |

`act` が `changed=1` を返したのに `before` と `after` が完全に同一で、
`force_new: true` の get だけが変化を示しました。

**`expect_recap` は件数しか見ないため、この状態でも `OK` と判定します。**
実際に `rc=0` で3ケースとも「成功」しながら、記録された内容には何の変化もありませんでした。
before/after の中身は必ず人が突き合わせてください。

なお `before` の再生成には副次的な効果もあります。example playbook の `set` タスクは
`force_new` を渡しておらず、モジュールの既定値は `False` なので、`set` は保存済みプロファイルを
基準に新しい並びを組み立てます。`before` で再生成しておくことで `act` の `set` が実態に基づいて動きます。

### 待機中の監視

長く待たされたときに「本当に進んでいるか」を別端末から確認できます。
モジュールは待機中もセッションの状況を syslog へ書いています（`-v` は不要です）。

```bash
# 端末2: 待機開始時のセッションURLと、以降60秒ごとの経過が出る
journalctl -t ansible-irmc_biosbootorder -f
#   journald が使えない環境では:  sudo tail -f /var/log/syslog | grep ansible-

# 出力されたセッションURLの詳細ログを読む
curl -sk -u <user>:<pw> https://<host>/sessionInformation/<id>/log \
  | jq -r '.SessionLog.Entries.Entry[] | "\(.["@date"]) \(.["#text"])"'
```

セッションが終わらないまま既定1時間を超えると、モジュールはタイムアウトして
セッションログのURL付きのメッセージで失敗します。無限に待ち続けることはありません。

## 機体ごとに値が異なる場合

`irmc_biosbootorder` のブートデバイス名のように、機体構成に依存して値が変わる項目があります。
実測では3台の間で**共通のデバイスが1つもありません**でした。

| 機種      | StructuredBootString                                                              |
| --------- | --------------------------------------------------------------------------------- |
| RX1330 M6 | `RAID.Slot.3.0`, `NIC.LOM.1.2.IPv4PXE`, `NIC.LOM.2.3.IPv4PXE`, …                  |
| RX1440 M2 | `HD.Emb.1.1`, `NIC.LOM.0.1.IPv4PXE`, `CD.Virtual.0.1.1`, …                        |
| RX2450 M2 | `NIC.LOM.0.1.IPv4PXE`, `RAID.Slot.11.237`, `NVMe.Slot.13.PN2.EFI_BOOT_BOOTX64`, … |

こうした値はケース定義に直接書けません。**`host_vars` に機体ごとの値を持たせます。**

`ansible-playbook` は**インベントリファイルと同じディレクトリ**の `host_vars/` を自動的に読みます。
このリポジトリでは `inventory.ini` をルートに置くことにしているので、`host_vars/` もルートに置きます
（`group_vars/` も同じ仕組みで読まれます）。

```text
inventory.ini
group_vars/
  all                 ← 全グループ共通
  iRMC_group.yml      ← ファイル名はグループ名と一致させる
host_vars/
  192.0.2.10.yml      ← ファイル名は inventory_hostname と完全一致させる
  192.0.2.11.yml
```

`group_vars/` と `host_vars/` はどちらも環境固有の値を置く場所なので、
`inventory.ini` と同じく `.gitignore` で除外されています。

```yaml
# host_vars/192.0.2.10.yml
---
boot_device: "NIC.LOM.2.3.IPv4PXE"
boot_key: "StructuredBootString"
```

`examples/modules/irmc_biosbootorder_examples.yml` は既に `{{ boot_device }}` を参照しているので、
プレイブック側の変更は不要でホストごとに解決されます。
さらに分割したい場合はディレクトリ形式にもできます（中の `.yml` が全てマージされます）。

```text
host_vars/
  192.0.2.10/
    boot.yml
    raid.yml
```

**重要**: `--extra-vars` は `host_vars` より優先度が高いため、
この方式を使うケースでは `vars` に同じ変数を書いてはいけません。
書くと全ホストが同じ値で上書きされ、`host_vars` が無視されます。

**`boot_device` の選び方**: 工場出荷時の並びで**先頭に来ないデバイス**を選んでください。
`set` ケースは `arrange` で `default` を実行してから `act` で `set` するため、
先頭に来るデバイスを選ぶと `act` の時点で既に目的の状態になっていて `set` が skip され、
`expect_recap` の `changed: 1` / `skipped: 0` に引っかかります。

工場出荷時の並びは `default` ケースの `after`、または以下で確認できます。

```bash
uv run ansible-playbook ./examples/modules/irmc_biosbootorder_examples.yml \
  -i inventory.ini --tags default --limit <host>     # 既定へ戻す(電源オフが必要)
uv run ansible-playbook ./examples/modules/irmc_biosbootorder_examples.yml \
  -i inventory.ini --tags get --limit <host>         # 並びを見る
```

`host_vars/` は機体固有情報なので `.gitignore` で除外済みです（`inventory.ini` と同じ扱い）。

## inventory に設定する変数

ケースによっては、iRMC の接続情報以外に環境固有の値が必要です。
`inventory.ini` は gitignore 済みなので、実環境の値をそのまま書けます。

### 仮想メディア（`irmc_setvm` / `irmc_connectvm`）

メディアサーバは全機体で共通なのでグループ変数に置きます。

```ini
[iRMC_group:vars]
validate_certificate=false
share_type=HTTPS
server=192.0.2.1
share=/iso
image=rhel-10.0-x86_64-dvd.iso
```

## ファームウェアを準備する

`irmc_fwbios_update` のケースは BIOS と iRMC のフラッシュに実際に書き込みます。
ファームウェアは `tests/manual/assets/firmware/` に置きます（**gitignore 済み**。
ベンダー提供のバイナリなのでリポジトリには入れません）。

パスは**機体ごとに違う**ので `host_vars/<host>.yml` に書きます。
`inventory.ini` や step の `vars` に書くと全ホストへ適用されてしまいます。

```yaml
# host_vars/<host>.yml   ※ host_vars/ は gitignore 済み
# パスは playbook のあるディレクトリ（examples/modules/）からの相対
bios_filename: "../../tests/manual/assets/firmware/RX1330M6/BIOS/.../D4133-A1.UPD"
irmc_filename: "../../tests/manual/assets/firmware/RX1330M6/iRMC/xxx.BIN"
```

| 変数            | 用途                                                                       |
| --------------- | -------------------------------------------------------------------------- |
| `bios_filename` | BIOS の更新ファイル                                                        |
| `irmc_filename` | iRMC の更新ファイル。書き込み先の面（`irmc_flash_selector`）の版に合わせる |

### 版の選び方

**実測されている制約は「BIOS は下げられない」ことだけです。** 上げる方向も、同じ版の焼き直しも
成功します。ダウングレードだけが iRMC 側で拒否され、モジュールは `TaskState: Exception` を
受け取って `status 21` で失敗します
（[`irmc_fwbios_update.py:453-455`](../../plugins/modules/irmc_fwbios_update.py#L453-L455)。
ダウングレード専用のコードではなく、更新タスクが失敗したときの汎用コードです）。
iRMC は上げる・下げる・同じ版のいずれも成功します。
方向ごとの実測結果は `tests/manual/cases/irmc_fwbios_update.yml` の冒頭コメントにあります。

**そのうえで、`host_vars` には現在と同じ版を置くことを推奨します。**
新しい版でも更新自体は成功しますが、テスト機の BIOS が実際に上がり、
**下げられない以上そこから元に戻せません。** リリース前のエビデンス取得のつもりで、
機体の版を不可逆に変えてしまうのは避けたいところです。
同じ版なら `before` / `after` に差分は出ませんが、
「更新手順が完走し、版数が壊れていない」ことのエビデンスにはなります。

### 適用前の確認

現在の版数とセレクタを確認してください。

```bash
uv run ./tests/manual/run_tests.py --cases tests/manual/cases/irmc_fwbios_update.yml \
  --name get --limit <host>
```

`irmc_flash_selector` と `irmc_boot_selector` が**別の面**を指していることも確認します。
同じ面だと動作中のファームを上書きすることになります。

サーバの電源はオフである必要があります。オンだとモジュールが `skipped` で抜けて更新されません。
ケース側で `ensure_power_state.yml` を使って落としているので、通常は意識不要です。

## テスト用アセット

ケースがモジュールへ渡すファイルは `tests/manual/assets/` に置きます。

| ディレクトリ        | git           | 内容                                                                          |
| ------------------- | ------------- | ----------------------------------------------------------------------------- |
| `assets/certs/`     | **gitignore** | `irmc_certificate` 用の自己署名証明書。`make` で生成する                      |
| `assets/firmware/`  | **gitignore** | `irmc_fwbios_update` 用の BIOS / iRMC イメージ                                |

どちらもリポジトリには入れません。ファームウェアはベンダー提供のバイナリで再配布条件が
不明なため、証明書は秘密鍵を含むためです。`assets/certs/` で追跡しているのは
`Makefile` と `README.md` だけです。

### ファイルパスは `examples/modules/` からの相対で書く

モジュールがファイルを読むときのカレントディレクトリは、**ランナーを起動したディレクトリではなく
プレイブックのあるディレクトリ**（`examples/modules/`）になります。
`irmc_certificate` の `read_keyfile()` は素の `open()` を使うため、ケース定義には次のように書きます。

```yaml
      vars:
        ssl_cert_path: "../../tests/manual/assets/certs/server2.crt"
```

リポジトリルートからの相対ではないので注意してください。次で実在を確認できます。

```bash
(cd examples/modules && ls -l ../../tests/manual/assets/certs/server2.crt)
```

### 登録された証明書を確認する

`irmc_certificate` の `get` は PEM をそのまま返すので、ソースファイルの base64 の一部が
エビデンスに含まれているかどうかで判定できます。PEM の2行目は証明書ごとに異なります。
エビデンス中では `\n` エスケープされた1行の JSON 文字列になっていますが、
この部分文字列はそのまま含まれるので `grep -F` で拾えます。

```bash
CERTS=tests/manual/assets/certs
OUT=tests/manual/results/irmc_certificate/set.txt

# before に server1、after に server2 が出ていれば期待どおり（どちらも 1 になる）
grep -cF "$(sed -n 2p $CERTS/server1.crt)" $OUT
grep -cF "$(sed -n 2p $CERTS/server2.crt)" $OUT
```

## 結果ファイル

`tests/manual/results/<module>/<name>.txt` に出力されます（`--results-dir` で変更可）。

```text
case: irmc_idled/set
source: tests/manual/cases/irmc_idled.yml
executed_at: 2026-08-08 12:34:56
================================================================================

################################################################################
# step 1/4: arrange
#   ID LEDを消灯し、act が必ず変更を伴うようにする
#   playbook:     examples/modules/irmc_idled_examples.yml
#   tag:          set
#   vars:         {"state": "Off"}
################################################################################
（ansible-playbook の出力）

################################################################################
# step 3/4: act
#   playbook:     examples/modules/irmc_idled_examples.yml
#   tag:          set
#   vars:         {"state": "Blinking"}
#   expect_recap: {"changed": 1, "failed": 0}
################################################################################
（ansible-playbook の出力）
[expect_recap] OK
```

（上の例では紙面の都合で罫線を80桁にしていますが、実際は `--columns` の値になります）

### 横幅

エビデンスは**実行した端末のサイズに関わらず一定の横幅**で出力されます。既定は120桁で、
`--columns` で変えられます。Ansible のバナー（`PLAY [...] ***`、`TASK [...] ***`）も
ステップ見出しの罫線も同じ幅になります。

固定していない場合、実行中に端末をリサイズするとファイルの途中で横幅が変わってしまいます。
Ansible はバナー幅を決めるのに疑似端末のサイズを `ioctl` で直接読んでおり、
**`COLUMNS` 環境変数では制御できない**ため、ランナー側で `script` が作る疑似端末のサイズを
`stty` で固定しています。

Ansible 側に下限があるため、`--columns` に80未満を指定しても80桁になります。

## 必要なもの

- `uv`
- `script`（util-linux）— `ansible-playbook` の出力をコンソールとファイルの両方へリアルタイムに流すために使います
