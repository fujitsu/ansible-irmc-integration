SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:

BITS        ?= 2048
CA_DAYS     ?= 3650
SERVER_DAYS ?= 365

# Subject は「実在の企業・地名と衝突しないこと」と「証明書だけを見て出所が辿れること」を
# 満たす値にしている。この証明書は Ansible では元に戻せず iRMC に残り続けるため、後日
# openssl x509 -subject で見た人が何のための証明書か分かる必要がある。
# ドメインは RFC 2606 で文書用に予約されている example.com 配下を使う。
#
# openssl の -subj は '/' が項目の区切りなので、値に含める '/' は '\/' とエスケープする。
# エスケープを忘れるとそれ以降の項目(CN を含む)が黙って捨てられる。
# verify ターゲットで CN を確認しているので、間違えれば必ず気付ける。
C  ?= JP
ST ?= Example
L  ?= Example
O  ?= iRMC Manual Test
OU ?= tests\/manual

CA_CN      ?= ca.irmc-test.example.com
SERVER1_CN ?= server1.irmc-test.example.com
SERVER2_CN ?= server2.irmc-test.example.com

CA_SUBJ := /C=$(C)/ST=$(ST)/L=$(L)/O=$(O)/OU=$(OU)/CN=$(CA_CN)

# サーバ証明書を2組作るのは、手動テストの arrange と act で別々の証明書を登録し、
# 何回実行しても before と after に差が出るようにするため。
# irmc_certificate の set は現在値を見ずに常に changed を返すので、同じ証明書を
# 登録し続けると before と after が同一になりエビデンスにならない。
SERVERS := server1 server2
CRTS    := $(addsuffix .crt,$(SERVERS))
KEYS    := $(addsuffix .key,$(SERVERS))

# openssl の Subject 表示は既定の -nameopt が版によって違い、"CN = x" と "CN=x" で揺れる。
# verify の grep が環境依存で落ちるため、RFC2253 を明示して形式を固定する。
# compat は OU の '/' を '\/' とエスケープしてしまうので使えない。
NAMEOPT := -nameopt RFC2253

.PHONY: all clean verify inspect

all: ca.crt $(CRTS) verify

# --- CA(明示ルールなので下のパターンルールより優先される) ---
ca.key:
	openssl genrsa -traditional -out $@ $(BITS)
	test "$$(head -n 1 $@)" = "-----BEGIN RSA PRIVATE KEY-----"

ca.crt: ca.key
	openssl req -new -x509 -key $< -sha256 -days $(CA_DAYS) -out $@ \
	  -subj "$(CA_SUBJ)" \
	  -addext "basicConstraints=critical,CA:TRUE" \
	  -addext "keyUsage=critical,keyCertSign,cRLSign" \
	  -addext "subjectKeyIdentifier=hash"

# --- サーバ証明書(CN だけがサーバごとに異なる) ---
server1.csr server1.ext: CN = $(SERVER1_CN)
server2.csr server2.ext: CN = $(SERVER2_CN)

# iRMC は openssl 3.x 形式の秘密鍵を受け付けないため -traditional が必須。
# ヘッダが "-----BEGIN RSA PRIVATE KEY-----" であることを毎回確認する。
%.key:
	openssl genrsa -traditional -out $@ $(BITS)
	test "$$(head -n 1 $@)" = "-----BEGIN RSA PRIVATE KEY-----"

%.csr: %.key
	openssl req -new -key $< -out $@ \
	  -subj "/C=$(C)/ST=$(ST)/L=$(L)/O=$(O)/OU=$(OU)/CN=$(CN)"

%.ext:
	printf '%s\n' \
	  'basicConstraints=CA:FALSE' \
	  'keyUsage=critical,digitalSignature,keyEncipherment' \
	  'extendedKeyUsage=serverAuth' \
	  'subjectAltName=DNS:$(CN)' \
	  > $@

%.crt: %.csr %.ext ca.crt ca.key
	openssl x509 -req -in $< -CA ca.crt -CAkey ca.key -CAcreateserial \
	  -out $@ -days $(SERVER_DAYS) -sha256 -extfile $*.ext

verify: ca.crt $(CRTS) $(KEYS)
	# Subject の '/' をエスケープし忘れると CN ごと欠落し、server1 と server2 が
	# 区別できなくなる。黙って壊れるので必ず確認する。
	openssl x509 -in ca.crt      -noout -subject $(NAMEOPT) | grep -qF "CN=$(CA_CN)"
	openssl x509 -in server1.crt -noout -subject $(NAMEOPT) | grep -qF "CN=$(SERVER1_CN)"
	openssl x509 -in server2.crt -noout -subject $(NAMEOPT) | grep -qF "CN=$(SERVER2_CN)"
	openssl x509 -in server1.crt -noout -subject $(NAMEOPT) | grep -qF "OU=tests/manual"
	for s in $(SERVERS); do
	  openssl verify -CAfile ca.crt $$s.crt
	  test "$$(head -n 1 $$s.key)" = "-----BEGIN RSA PRIVATE KEY-----"
	  diff -u <(openssl x509 -in $$s.crt -noout -pubkey) \
	          <(openssl rsa -in $$s.key -pubout 2>/dev/null)
	done
	echo "OK"

inspect: ca.crt $(CRTS)
	echo "== CA =="
	openssl x509 -in ca.crt -noout -subject -issuer -dates
	for s in $(SERVERS); do
	  echo
	  echo "== $$s =="
	  openssl x509 -in $$s.crt -noout -subject -issuer -dates -ext subjectAltName
	done

clean:
	rm -f ca.key ca.crt ca.srl $(addsuffix .key,$(SERVERS)) \
	      $(addsuffix .csr,$(SERVERS)) $(addsuffix .ext,$(SERVERS)) $(CRTS)
