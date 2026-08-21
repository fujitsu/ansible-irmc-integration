# Copyright 2018-2024 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division)
__metaclass__ = type

import time
import traceback
import json

try:
    import requests
    from requests.auth import HTTPBasicAuth
    from requests.adapters import HTTPAdapter
    import urllib3
    from urllib3.util.retry import Retry
    from urllib3.exceptions import InsecureRequestWarning
    urllib3.disable_warnings(InsecureRequestWarning)
    HAS_REQUESTS = True
except:
    HAS_REQUESTS = False


def irmc_redfish_get(module, uri):
    if not HAS_REQUESTS:
        return 90, "Python 'requests' module not found.", "iRMC module requires 'requests' Module"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    url = "https://{0}/{1}".format(module.params['irmc_url'], uri)

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1)
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    msg = "OK"
    try:
        data = session.get(url, headers=headers, verify=module.params['validate_certs'],
                           auth=HTTPBasicAuth(module.params['irmc_username'], module.params['irmc_password']))
        data.connection.close()

        status = data.status_code
        if status != 200:
            try:
                msg = "GET request was not successful ({0}): status {1}, '{2}'". \
                      format(url, status, data.json()['error']['message'])
            except Exception:
                msg = "GET request was not successful ({0}), status {1}.".format(url, status)

    except Exception as e:
        status = 99
        data = traceback.format_exc()
        msg = "GET request encountered exception ({0}): {1}".format(url, str(e))

    return status, data, msg


def irmc_redfish_patch(module, uri, body, etag):
    if not HAS_REQUESTS:
        return 90, "Python 'requests' module not found.", "iRMC access requires 'requests' Module"

    etag = str(etag)
    if not etag.isdigit():
        msg = "etag is no number: {0}".format(etag)
        data = msg
        return 97, data, msg

    if body != "":
        try:
            json.loads(body)
        except ValueError as e:
            data = traceback.format_exc()
            msg = "PATCH request got invalid JSON body: {0}".format(body)
            return 98, data, msg

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "If-Match": etag
    }
    url = "https://{0}/{1}".format(module.params['irmc_url'], uri)

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1)
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    msg = "OK"
    try:
        data = session.patch(url, headers=headers, data=body, verify=module.params['validate_certs'],
                             auth=HTTPBasicAuth(module.params['irmc_username'], module.params['irmc_password']))
        data.connection.close()

        status = data.status_code
        if status != 200:
            try:
                msg = "PATCH request was not successful ({0}): status {1}, '{2}'". \
                      format(url, status, data.json()['error']['message'])
            except Exception:
                msg = "PATCH request was not successful ({0}), status {1}.".format(url, status)

    except Exception as e:
        status = 99
        data = traceback.format_exc()
        msg = "PATCH request encountered exception ({0}): {1}".format(url, str(e))

    return status, data, msg


def irmc_redfish_post(module, uri, body):
    if not HAS_REQUESTS:
        return 90, "Python 'requests' module not found.", "iRMC module requires 'requests' Module"

    if body != "":
        try:
            json.loads(body)
        except ValueError as e:
            data = traceback.format_exc()
            msg = "POST request got invalid JSON body: {0}".format(body)
            return 98, data, msg

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    url = "https://{0}/{1}".format(module.params['irmc_url'], uri)

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1)
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    msg = "OK"
    try:
        data = session.post(url, headers=headers, data=body, verify=module.params['validate_certs'],
                            auth=HTTPBasicAuth(module.params['irmc_username'], module.params['irmc_password']))
        data.connection.close()

        status = data.status_code
        if status not in (200, 202, 204):
            try:
                msg = "POST request was not successful ({0}): {1}".format(url, data.json()['error']['message'])
            except Exception:
                msg = "POST request was not successful ({0}).".format(url)

    except Exception as e:
        status = 99
        data = traceback.format_exc()
        msg = "POST request encountered exception ({0}): {1}".format(url, str(e))

    return status, data, msg


def irmc_redfish_put(module, uri, body):
    if not HAS_REQUESTS:
        return 90, "Python 'requests' module not found.", "iRMC module requires 'requests' Module"

    if body != "":
        try:
            json.loads(body)
        except ValueError as e:
            data = traceback.format_exc()
            msg = "POST request got invalid JSON body: {0}".format(body)
            return 98, data, msg

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    url = "https://{0}/{1}".format(module.params['irmc_url'], uri)

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1)
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    msg = "OK"
    try:
        data = session.put(url, headers=headers, data=body, verify=module.params['validate_certs'],
                           auth=HTTPBasicAuth(module.params['irmc_username'], module.params['irmc_password']))
        data.connection.close()

        status = data.status_code
        if status not in (200, 202, 204):
            try:
                msg = "PUT request was not successful ({0}): {1}".format(url, data.json()['error']['message'])
            except Exception:
                msg = "PUT request was not successful ({0}).".format(url)

    except Exception as e:
        status = 99
        data = traceback.format_exc()
        msg = "PUT request encountered exception ({0}): {1}".format(url, str(e))

    return status, data, msg


def irmc_redfish_delete(module, uri):
    if not HAS_REQUESTS:
        return 90, "Python 'requests' module not found.", "iRMC module requires 'requests' Module"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    url = "https://{0}/{1}".format(module.params['irmc_url'], uri)

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1)
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    msg = "OK"
    try:
        data = session.delete(url, headers=headers, verify=module.params['validate_certs'],
                              auth=HTTPBasicAuth(module.params['irmc_username'], module.params['irmc_password']))
        data.connection.close()

        status = data.status_code
        if status != 200:
            try:
                msg = "DELETE request was not successful ({0}): {1}".format(url, data.json()['error']['message'])
            except Exception:
                msg = "DELETE request was not successful ({0}).".format(url)

    except Exception as e:
        status = 99
        data = traceback.format_exc()
        msg = "DELETE request encountered exception ({0}): {1}".format(url, str(e))

    return status, data, msg


def get_irmc_json(jsondata, keys):
    if isinstance(keys, list):
        jsonkey = " ".join(keys)
    else:
        jsonkey = keys
        keys = [keys]

    keylen = len(keys)
    try:
        if keylen == 1:
            data = jsondata[keys[0]]
        elif keylen == 2:
            data = jsondata[keys[0]][keys[1]]
        elif keylen == 3:
            data = jsondata[keys[0]][keys[1]][keys[2]]
        elif keylen == 4:
            data = jsondata[keys[0]][keys[1]][keys[2]][keys[3]]
        elif keylen == 5:
            data = jsondata[keys[0]][keys[1]][keys[2]][keys[3]][keys[4]]
        elif keylen == 6:
            data = jsondata[keys[0]][keys[1]][keys[2]][keys[3]][keys[4]][keys[5]]
        else:
            data = "Key too long ({0} levels): '{1}'".format(keylen, jsonkey)
    except Exception:
        data = "Key does not exist: '{0}'".format(jsonkey)

    return data


def waitForSessionToFinish(module, sessionId, timeout=3600, poll_interval=10,
                           error_retries=6, log_interval=60):
    """指定されたiRMCセッションが終了するまで待機します。

    プロファイル関連の処理は、iRMCがサーバをgraceful shutdownさせてBIOSパラメータを
    バックアップしてから進むため数分かかります(RX2450 M2でブート順取得が実測7分38秒、
    ブート順の既定復帰が実測約10分半)。
    待機中の状況は module.log() でsyslogへ即座に書き出すため、モジュールの実行中でも
    別端末から追えます(module.warn() はモジュール終了までバッファされるため使えません)。

        journalctl -t ansible-<コレクション名>.<モジュール名> -f

    引数:

        module        - AnsibleModuleオブジェクト
        sessionId     - 待機対象のセッションID
        timeout       - 全体の制限時間(秒)。ファームウェア更新など正当に長時間かかる処理が
                        あるため既定値は大きく取っており、無限ループを防ぐことだけが目的
        poll_interval - ポーリング間隔(秒)
        error_retries - 許容する連続通信エラー回数。iRMCはプロファイル処理中に一時的に
                        接続を拒否することがあり、HTTP層のリトライは約3秒しか粘らない
        log_interval  - 進捗メッセージを出す間隔(秒)

    戻り値:

        int   - HTTPステータス、または28(タイムアウト)・29(セッションがエラー終了)
        object - レスポンスデータ
        str   - 結果メッセージ

    注意事項:

        - timeoutを超えた場合はstatus 28とセッションログのURLを含むメッセージを返す
        - 通信エラーはerror_retries回まで再試行し、超えたらそのstatusを返す
        - HTTPレベルのエラー(404など)は再試行せず即座に返す
    """
    session_url = "https://{0}/sessionInformation/{1}".format(module.params['irmc_url'], sessionId)
    # waitForIrmcSessionsInactive() は終了済みのセッションに対しても呼ぶため、実際に待つことに
    # なったときだけ出す。そうしないと本命のセッションが終了済みセッションのログに埋もれる。
    waiting_msg = "Waiting for session {0} to finish (timeout {1}s). Session log: {2}/log".format(
        sessionId, timeout, session_url)
    announced = False

    started = time.time()
    deadline = started + timeout
    last_log = started
    consecutive_errors = 0
    while True:
        status, sdata, msg = irmc_redfish_get(module, "sessionInformation/{0}/status".format(sessionId))
        if status < 100:
            # Transport error. Retry, since this is often transient.
            if not announced:
                module.log(waiting_msg)
                announced = True
            consecutive_errors += 1
            module.log("Session {0}: request failed ({1}/{2}): {3}".format(
                sessionId, consecutive_errors, error_retries, msg))
            if consecutive_errors > error_retries or time.time() >= deadline:
                return status, sdata, msg
            time.sleep(poll_interval)
            continue
        if status not in (200, 202, 204):
            return status, sdata, msg
        consecutive_errors = 0

        sstatus = get_irmc_json(sdata.json(), ["Session", "Status"])
        if "terminated" not in sstatus:
            if not announced:
                module.log(waiting_msg)
                announced = True
            now = time.time()
            if now >= deadline:
                msg = ("Timeout ({0}s) waiting for session {1} to finish "
                       "(last status: '{2}'). See {3}/log").format(
                    timeout, sessionId, sstatus, session_url)
                return 28, sdata, msg
            if now - last_log >= log_interval:
                module.log("Session {0} still '{1}' after {2}s (timeout {3}s)".format(
                    sessionId, sstatus, int(now - started), timeout))
                last_log = now
            time.sleep(poll_interval)
        else:
            msg = "Session result: {0}".format(sstatus)
            if "error" in sstatus:
                status, sdata, mmsg = irmc_redfish_get(module, "sessionInformation/{0}/log".format(sessionId))
                if status < 100 or (status not in (200, 202, 204)):
                    return status, sdata, mmsg
                sdata = sdata.json()
                status = 29
            break
    return status, sdata, msg


def elcm_check_status(module):
    status, data, msg = irmc_redfish_get(module, "rest/v1/Oem/eLCM/eLCMStatus")
    if status < 100 or (status not in (200, 202, 204)):
        return status, data, msg

    if get_irmc_json(data.json(), ["eLCMStatus", "EnabledAndLicenced"]) == "false":
        msg = "eLCM functionality can onlybe used when iRMC is supplied with a valid eLCM license!"
        status = 20
    if get_irmc_json(data.json(), ["eLCMStatus", "SDCardMounted"]) == "false":
        msg = "eLCM requires iRMC to be supplied with a eLCM SD card!"
        status = 21

    return status, data, msg
