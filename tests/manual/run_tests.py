#!/usr/bin/env python3
"""examples/modules/ 配下のプレイブックをテストケース定義に従って実行し、
結果を tests/manual/results/ 配下のファイルへ保存します。

1つのテストケースは名前付きステップ(プレイブック実行)の列として定義します。
set 本体も、その前処理も、後の状態確認も、電源状態を揃える処理も、すべて同じ形の
ステップとして記述します。スキーマの詳細は tests/manual/README_ja.md を参照してください。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CASES_DIR = SCRIPT_DIR / 'cases'
DEFAULT_INVENTORY = REPO_ROOT / 'inventory.ini'
DEFAULT_PLAYBOOK_DIR = REPO_ROOT / 'examples' / 'modules'
DEFAULT_RESULTS_DIR = SCRIPT_DIR / 'results'
RUNNER_PREFIX = ['uv', 'run']

# エビデンスの横幅。Ansible は疑似端末のサイズを ioctl で直接読んでバナー幅を決めるため
# (COLUMNS 環境変数は見ない)、端末をリサイズするとステップごとに幅が変わってしまう。
# script が作る疑似端末のサイズを stty で固定して、実行環境によらず一定幅にする。
#
# Ansible のバナー長は疑似端末の桁数そのものになる。Display._set_column_width() が
# self.columns = max(79, 桁数 - 1) とし、banner() が "msg + ' ' + '*' * (columns - len(msg))"
# を出すため、合計は columns + 1 = max(80, 桁数) となる。
DEFAULT_COLUMNS = 120
MIN_COLUMNS = 80    # 上式の下限。これ未満を指定してもバナーは80桁になる
PTY_ROWS = 50       # Ansible は行数を見ないが、0行の疑似端末を避けるため設定する

# ステップ見出しのキーは ':' の縦位置を揃える。ステップごとに桁がずれないよう、
# 幅は出現するキーからではなく最長のキーに固定する。
STEP_HEADER_KEY_WIDTH = len('expect_recap:')

RECAP_HEADER_RE = re.compile(r'^PLAY RECAP\s*\**\s*$')
# 統計キーは ok/changed/failed 等の小文字語に限られる。ここを `\w` にすると数字を含むため
# 直後の `\d+` と食い合い、マッチ失敗時に指数的バックトラッキング（ReDoS）が起きる。
# 文字クラスを排他にして曖昧さを無くしている。
RECAP_LINE_RE = re.compile(r'^(?P<host>\S+)\s*:\s*(?P<stats>(?:[a-z]+=\d+\s*)+)$')
RECAP_STAT_RE = re.compile(r'([a-z]+)=(\d+)')

# expect_recap にこれらのいずれかが 1 以上で書かれていたら、そのステップは
# ansible-playbook が非0で終了することを期待しているとみなす。
FAILURE_STATS = ('failed', 'unreachable')

INVENTORY_TEMPLATE_HINT = """\
inventory.ini が見つかりません: {path}

例:
[iRMC_group]
<ipaddress> irmc_user=admin irmc_password=<pwd>

[iRMC_group:vars]
validate_certs=false
"""


class CaseDefinitionError(Exception):
    """テストケース定義の記述誤りを表す例外です。"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """コマンドライン引数を解析します。

    引数:

        argv - 解析対象の引数リスト(省略時は sys.argv から取得)

    戻り値:

        argparse.Namespace - 解析結果
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-c',
        '--cases',
        nargs='*',
        type=Path,
        default=None,
        help='テストケース定義ファイルまたはディレクトリ(複数指定可、省略時は cases/ 配下すべて)',
    )
    parser.add_argument('--name', default=None, help='実行するケースを name の部分一致で絞り込む')
    parser.add_argument(
        '--limit',
        default=None,
        help='対象ホストを絞り込む(ansible-playbook --limit にそのまま渡す)',
    )
    parser.add_argument(
        '--columns',
        type=int,
        default=DEFAULT_COLUMNS,
        help=f'エビデンスの横幅(既定 {DEFAULT_COLUMNS})。'
             f'Ansible 側の下限により {MIN_COLUMNS} 未満を指定しても {MIN_COLUMNS} になる',
    )
    parser.add_argument('--inventory', type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument('--playbook-dir', type=Path, default=DEFAULT_PLAYBOOK_DIR)
    parser.add_argument('--results-dir', type=Path, default=DEFAULT_RESULTS_DIR)
    return parser.parse_args(argv)


def resolve_case_files(paths: list[Path] | None, default_dir: Path) -> list[Path]:
    """テストケース定義ファイルのパス群を、実際に読み込むYAMLファイルの一覧に展開します。

    引数:

        paths       - CLIで指定されたファイルまたはディレクトリのパス一覧(未指定時 None)
        default_dir - paths が None の場合に走査するデフォルトディレクトリ

    戻り値:

        list[Path] - 読み込み対象のYAMLファイルパスのリスト(ソート済み)
    """
    targets = paths or [default_dir]
    files: list[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(target.glob('*.yml'))
        else:
            files.append(target)
    return sorted(set(files))


def validate_case(case: dict) -> None:
    """テストケース定義1件の必須キーを検証します。

    引数:

        case - 検証対象のテストケース定義

    注意事項:

        - name / steps が無い場合は CaseDefinitionError を送出する
        - steps の各要素に name が無い場合、playbook を解決できない場合も同様
    """
    label = f'{case.get("_source_file")} の {case.get("name") or case.get("module") or "(名前なし)"}'
    if not case.get('name'):
        msg = f'{label}: ケースに name がありません'
        raise CaseDefinitionError(msg)
    steps = case.get('steps')
    if not isinstance(steps, list) or not steps:
        msg = f'{label}: ケースに steps(1件以上のリスト)がありません'
        raise CaseDefinitionError(msg)
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict) or not step.get('name'):
            msg = f'{label}: {index}番目のステップに name がありません'
            raise CaseDefinitionError(msg)
        if not step.get('playbook') and not case.get('playbook'):
            msg = (
                f'{label}: ステップ {step.get("name")} の playbook を解決できません'
                '(ステップかケースのどちらかに playbook が必要です)'
            )
            raise CaseDefinitionError(msg)


def load_test_cases(case_files: list[Path]) -> list[dict]:
    """複数のテストケース定義ファイルを読み込み、1つのリストに結合します。

    引数:

        case_files - 読み込むYAMLファイルパスのリスト

    戻り値:

        list[dict] - module を補完し、検証済みのテストケースのリスト

    注意事項:

        - 定義に不備がある場合は CaseDefinitionError を送出する
    """
    cases: list[dict] = []
    for case_file in case_files:
        with case_file.open(encoding='utf-8') as f:
            raw_cases = yaml.safe_load(f) or []
        for raw_case in raw_cases:
            case = dict(raw_case)
            case['_source_file'] = case_file
            if not case.get('module') and case.get('playbook'):
                case['module'] = Path(case['playbook']).stem.removesuffix('_examples')
            validate_case(case)
            if not case.get('module'):
                msg = f'{case_file} の {case["name"]}: module を決定できません'
                raise CaseDefinitionError(msg)
            cases.append(case)
    return cases


def filter_test_cases(cases: list[dict], keyword: str | None) -> list[dict]:
    """ケース名がキーワードに部分一致するテストケースだけを残します。

    モジュール単位の選択は読み込むファイルの指定(--cases)が担うため、
    ここでは name だけを見ます。

    引数:

        cases   - フィルタ対象のテストケース一覧
        keyword - name に部分一致させる文字列(None なら全件)

    戻り値:

        list[dict] - フィルタ後のテストケース一覧
    """
    if not keyword:
        return cases
    return [case for case in cases if keyword in case['name']]


def check_inventory(inventory_path: Path) -> None:
    """インベントリファイルの存在を確認します。存在しなければ案内を表示して終了します。

    引数:

        inventory_path - 確認するインベントリファイルのパス
    """
    if not inventory_path.exists():
        print(INVENTORY_TEMPLATE_HINT.format(path=inventory_path), file=sys.stderr)
        raise SystemExit(1)


def resolve_playbook(step: dict, case: dict, playbook_dir: Path) -> Path:
    """ステップが実行するプレイブックの絶対パスを決定します。

    値に '/' を含む場合はリポジトリルートからの相対パス、含まない場合は playbook_dir
    からの相対パスとして解決します。ステップに playbook が無ければケースの値を使います。

    引数:

        step         - ステップ定義
        case         - ステップが属するテストケース定義
        playbook_dir - ファイル名のみ指定された場合の基準ディレクトリ

    戻り値:

        Path - プレイブックの絶対パス
    """
    playbook = step.get('playbook') or case['playbook']
    if '/' in playbook:
        return REPO_ROOT / playbook
    return playbook_dir / playbook


def build_command(
    playbook_path: Path,
    inventory_path: Path,
    tag: str | None,
    extra_vars: dict,
    limit: str | None = None,
) -> list[str]:
    """ansible-playbook を実行するコマンドライン(リスト形式)を組み立てます。

    引数:

        playbook_path  - 実行対象のプレイブックのパス
        inventory_path - 使用するインベントリファイルのパス
        tag            - --tags に渡すタグ名(None ならタグを指定しない)
        extra_vars     - --extra-vars として渡す変数の辞書
        limit          - --limit に渡すホストパターン(None なら全ホストが対象)

    戻り値:

        list[str] - subprocess に渡すコマンドライン
    """
    cmd = [*RUNNER_PREFIX, 'ansible-playbook', str(playbook_path), '-i', str(inventory_path)]
    if tag:
        cmd += ['--tags', tag]
    if limit:
        cmd += ['--limit', limit]
    if extra_vars:
        cmd += ['--extra-vars', json.dumps(extra_vars)]
    return cmd


def run_via_script(cmd: list[str], result_file: Path, cwd: Path, env: dict, columns: int) -> int:
    """コマンドを script 経由で実行し、コンソールへリアルタイム表示しつつ結果ファイルへ追記します。

    script コマンドで疑似端末を割り当てることで、ansible-playbook が非tty出力時に
    バッファリングを強めてしまう問題を避け、実行中の出力がその場でコンソールにも
    表示されるようにします。

    疑似端末のサイズは stty で固定します。Ansible はバナー幅を決めるのに疑似端末のサイズを
    ioctl で直接読んでおり(COLUMNS 環境変数は見ない)、固定しないと端末をリサイズしたときに
    ステップごとにエビデンスの横幅が変わってしまうためです。

    引数:

        cmd         - 実行するコマンドライン(リスト形式)
        result_file - 出力を追記するファイルのパス
        cwd         - コマンドの実行時カレントディレクトリ
        env         - コマンドに渡す環境変数
        columns     - エビデンスの横幅

    戻り値:

        int - 実行したコマンドの終了コード
    """
    ansible_cmd = shlex.join(cmd)
    print(f'$ {ansible_cmd}')
    # Ansible のバナー長は疑似端末の桁数そのものになるので、そのまま指定する。
    # '&&' ではなく ';' で繋ぐことで、stty が失敗しても ansible-playbook の終了コードが
    # script -e にそのまま伝わるようにする。
    inner_cmd = f'stty cols {columns} rows {PTY_ROWS}; {ansible_cmd}'
    proc = subprocess.run(
        ['script', '-q', '-e', '-f', '-a', '-c', inner_cmd, str(result_file)],
        cwd=cwd,
        env=env,
        check=False,
    )
    return proc.returncode


def parse_recap(text: str) -> dict[str, dict[str, int]]:
    """ansible-playbook の出力から PLAY RECAP を抽出し、ホスト毎の統計値へ変換します。

    引数:

        text - ansible-playbook の出力テキスト

    戻り値:

        dict[str, dict[str, int]] - ホスト名をキー、統計値(ok/changed/failed など)の
                                    辞書を値とする辞書。RECAP が無ければ空辞書
    """
    recap: dict[str, dict[str, int]] = {}
    in_recap = False
    for raw_line in text.splitlines():
        # script は疑似端末なので行末に '\r' が残ることがある
        line = raw_line.rstrip()
        if RECAP_HEADER_RE.match(line):
            in_recap = True
            continue
        if not in_recap:
            continue
        if not line.strip():
            continue
        match = RECAP_LINE_RE.match(line)
        if match is None:
            break
        recap[match.group('host')] = {key: int(value) for key, value in RECAP_STAT_RE.findall(match.group('stats'))}
    return recap


def expects_failure(expect_recap: dict[str, int] | None) -> bool:
    """expect_recap がステップの失敗を期待しているかを判定します。

    専用のキー(expect_failure など)を設けず expect_recap から導出するのは、意図の記述箇所を
    1つに保ち、期待する統計値と食い違う余地を無くすためです。あわせて「何かは分からないが
    失敗した」という粗いテストを書けないようにする狙いもあります。

    引数:

        expect_recap - ステップの expect_recap(未指定なら None)

    戻り値:

        bool - failed または unreachable に 1 以上が指定されていれば True
    """
    if not expect_recap:
        return False
    return any(expect_recap.get(key, 0) > 0 for key in FAILURE_STATS)


def check_expect_recap(expected: dict[str, int], recap: dict[str, dict[str, int]]) -> list[str]:
    """PLAY RECAP の実測値を期待値と突き合わせ、不一致の内容を返します。

    expected に書かれたキーだけを検査し、RECAP に現れる全ホストが一致することを求めます。

    引数:

        expected - 期待する統計値(例 {'changed': 1, 'failed': 0})
        recap    - parse_recap() の戻り値

    戻り値:

        list[str] - 不一致の説明文のリスト。すべて一致した場合は空リスト
    """
    if not recap:
        return ['PLAY RECAP が見つかりませんでした']
    errors: list[str] = []
    for host, stats in sorted(recap.items()):
        diffs = [
            f'{key}={stats.get(key)}(期待値 {value})' for key, value in expected.items() if stats.get(key) != value
        ]
        if diffs:
            errors.append(f'{host}: ' + ', '.join(diffs))
    return errors


def append_lines(result_file: Path, lines: list[str], *, echo: bool = True) -> None:
    """結果ファイルへ行を追記し、必要ならコンソールにも表示します。

    引数:

        result_file - 追記先のファイルパス
        lines       - 追記する行のリスト(改行は含めない)
        echo        - True の場合はコンソールにも表示する
    """
    with result_file.open('a', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')
    if echo:
        for line in lines:
            print(line)


def format_step_header(step: dict, index: int, total: int, playbook_path: Path,
                       config: RunnerConfig) -> list[str]:
    """結果ファイルに書くステップ見出しの行を組み立てます。

    罫線の幅は config.columns に合わせます。Ansible のバナーと同じ幅にすることで
    ファイル全体が一定幅で揃います。

    引数:

        step          - ステップ定義
        index         - 1始まりのステップ番号
        total         - ステップの総数
        playbook_path - このステップが実行するプレイブックの絶対パス
        config        - 1回の実行を通して変わらない設定

    戻り値:

        list[str] - 見出しの行のリスト
    """
    rule = '#' * config.columns
    lines = [
        '',
        rule,
        f'# step {index}/{total}: {step["name"]}',
    ]
    if step.get('description'):
        lines.append(f'#   {step["description"]}')

    # --playbook-dir にリポジトリ外を指定できるため、相対化できない場合は絶対パスのまま出す
    display_path = playbook_path.relative_to(REPO_ROOT) if playbook_path.is_relative_to(REPO_ROOT) else playbook_path
    fields = [('playbook', display_path), ('tag', step.get('tag') or '(なし)')]
    if config.limit:
        fields.append(('limit', config.limit))
    if step.get('vars'):
        fields.append(('vars', json.dumps(step['vars'], ensure_ascii=False)))
    if step.get('expect_recap'):
        fields.append(('expect_recap', json.dumps(step['expect_recap'], ensure_ascii=False)))
    lines += [f'#   {key + ":":<{STEP_HEADER_KEY_WIDTH}} {value}' for key, value in fields]

    lines.append(rule)
    return lines


@dataclass(frozen=True)
class RunnerConfig:
    """1回の実行を通して変わらない設定をまとめたものです。"""

    playbook_dir: Path
    inventory_path: Path
    results_dir: Path
    limit: str | None
    columns: int


@dataclass(frozen=True)
class StepContext:
    """1つのテストケースを実行する間、全ステップで共通して使う値をまとめたものです。"""

    case: dict
    result_file: Path
    env: dict
    config: RunnerConfig


def run_step(step: dict, index: int, total: int, ctx: StepContext) -> dict:
    """ステップ1件(プレイブック実行1回)を行い、結果ファイルへ追記します。

    実行前後の結果ファイルのサイズ差から、そのステップの出力だけを取り出して
    PLAY RECAP を検証します。

    通常は ansible-playbook が正常終了することを成功とみなしますが、expect_recap に
    failed / unreachable が 1 以上で指定されている場合は逆に非0終了を期待します
    (expects_failure() を参照)。正常終了してしまった場合は失敗として扱うため、
    「拒否されるはずの操作が通ってしまった」という危険な結果が NG として現れます。

    引数:

        step  - ステップ定義
        index - 1始まりのステップ番号
        total - ステップの総数
        ctx   - ケース共通の実行コンテキスト

    戻り値:

        dict - name, ok, exit_code, errors を含む実行結果
    """
    config = ctx.config
    result_file = ctx.result_file
    playbook_path = resolve_playbook(step, ctx.case, config.playbook_dir)
    limit = config.limit
    header = format_step_header(step, index, total, playbook_path, config)
    append_lines(result_file, header, echo=False)
    print(f'[STEP] {index}/{total} {step["name"]}')

    offset = result_file.stat().st_size
    cmd = build_command(playbook_path, config.inventory_path, step.get('tag'), step.get('vars') or {}, limit)
    exit_code = run_via_script(cmd, result_file, REPO_ROOT, ctx.env, config.columns)

    errors: list[str] = []
    expect_recap = step.get('expect_recap')
    want_failure = expects_failure(expect_recap)
    if expect_recap:
        with result_file.open('rb') as f:
            f.seek(offset)
            output = f.read().decode('utf-8', errors='replace')
        recap = parse_recap(output)
        errors = check_expect_recap(expect_recap, recap)
        # limit の指定先が inventory に無いと 0 ホストで正常終了し PLAY RECAP が出ない
        if not recap and limit:
            errors.append(f"limit '{limit}' に一致するホストが inventory にあるか確認してください")
        # 失敗を期待したのに通ってしまった場合、RECAP の差分だけでは意図が読み取りにくいので明示する
        if want_failure and exit_code == 0:
            errors.append('失敗を期待するステップですが ansible-playbook が正常終了しました')
        verdict = 'NG' if errors else 'OK'
        suffix = ' (失敗を期待するステップ)' if want_failure else ''
        append_lines(result_file, [f'[expect_recap] {verdict}{suffix}', *(f'[expect_recap]   {e}' for e in errors)])

    rc_ok = exit_code != 0 if want_failure else exit_code == 0
    return {'name': step['name'], 'ok': rc_ok and not errors, 'exit_code': exit_code, 'errors': errors}


def run_case(case: dict, config: RunnerConfig) -> dict:
    """1件のテストケースを実行し、結果を results 配下のファイルに保存します。

    steps を先頭から順に実行します。あるステップが失敗し、そのステップに
    continue_on_error: true が無い場合は、そのケースを中断します。

    引数:

        case   - テストケース定義の辞書
        config - 1回の実行を通して変わらない設定

    戻り値:

        dict - name, module, status(pass・fail・skip), failed_step, result_file を含む実行結果
    """
    module = case['module']
    name = case['name']
    steps = case['steps']

    missing = [
        str(resolve_playbook(step, case, config.playbook_dir))
        for step in steps
        if not resolve_playbook(step, case, config.playbook_dir).exists()
    ]
    if missing:
        print(f'[SKIP] {module}/{name} - プレイブックが見つかりません: {", ".join(sorted(set(missing)))}')
        return {'name': name, 'module': module, 'status': 'skip', 'failed_step': None, 'result_file': None}

    result_file = config.results_dir / module / f'{name}.txt'
    result_file.parent.mkdir(parents=True, exist_ok=True)
    with result_file.open('w', encoding='utf-8') as f:
        f.write(f'case: {module}/{name}\n')
        f.write(f'source: {case["_source_file"]}\n')
        f.write(f'executed_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write('=' * config.columns + '\n')

    print(f'[RUN ] {module}/{name}')

    env = os.environ.copy()
    env['ANSIBLE_NOCOLOR'] = '1'
    ctx = StepContext(case=case, result_file=result_file, env=env, config=config)

    failed_step = None
    for index, step in enumerate(steps, start=1):
        step_result = run_step(step, index, len(steps), ctx)
        if step_result['ok']:
            continue
        if failed_step is None:
            failed_step = step_result['name']
        if not step.get('continue_on_error'):
            append_lines(result_file, [f'[abort] ステップ {step_result["name"]} が失敗したためこのケースを中断します'])
            break

    status = 'fail' if failed_step else 'pass'
    print(f'[{"OK" if status == "pass" else "NG"}] {module}/{name} -> {result_file}')

    return {'name': name, 'module': module, 'status': status, 'failed_step': failed_step, 'result_file': result_file}


def print_summary(results: list[dict]) -> None:
    """全テストケースの実行結果サマリをコンソールに表示します。

    引数:

        results - run_case() の戻り値のリスト
    """
    print('\n=== summary ===')
    counts = {'pass': 0, 'fail': 0, 'skip': 0}
    marks = {'pass': 'OK', 'fail': 'NG', 'skip': 'SKIP'}
    for result in results:
        counts[result['status']] += 1
        detail = f' (step: {result["failed_step"]})' if result['failed_step'] else ''
        print(f'{marks[result["status"]]}: {result["module"]}/{result["name"]}{detail}')
    print(f'\n合計: {len(results)}  成功: {counts["pass"]}  失敗: {counts["fail"]}  スキップ: {counts["skip"]}')


def main() -> int:
    """コマンドライン引数を解釈し、テストケースを順に実行します。

    戻り値:

        int - 失敗したテストケースが1件でもあれば1、無ければ0
    """
    args = parse_args()
    check_inventory(args.inventory)

    case_files = resolve_case_files(args.cases, DEFAULT_CASES_DIR)
    if not case_files:
        print('テストケース定義ファイルが見つかりません。', file=sys.stderr)
        return 1

    try:
        cases = filter_test_cases(load_test_cases(case_files), args.name)
    except CaseDefinitionError as exc:
        print(f'テストケース定義に誤りがあります: {exc}', file=sys.stderr)
        return 1

    if not cases:
        print('実行対象のテストケースがありません。')
        return 1

    config = RunnerConfig(
        playbook_dir=args.playbook_dir,
        inventory_path=args.inventory,
        results_dir=args.results_dir,
        limit=args.limit,
        # Ansible のバナーは MIN_COLUMNS 桁より狭くならない。罫線とバナーが必ず揃うよう、
        # ここでも同じ下限を適用する。
        columns=max(MIN_COLUMNS, args.columns),
    )

    try:
        results = [run_case(case, config) for case in cases]
    except FileNotFoundError as exc:
        print(
            f'コマンドが見つかりません: {exc}. uv と script(util-linux) が導入されていることを確認してください。',
            file=sys.stderr,
        )
        return 1

    print_summary(results)
    return 1 if any(r['status'] == 'fail' for r in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
