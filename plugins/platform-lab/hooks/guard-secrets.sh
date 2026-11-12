#!/usr/bin/env bash
# 資格情報の読み取りと出力を止める。判定規則は 03 の「各 hook の判定規則」。
# 確実な柵は sandbox の読み取り禁止（P3-01）が受け持つ。
set -uo pipefail
HOOK_NAME=guard-secrets
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_jq
read_input

# パス 1 つが資格情報の置き場所に当たれば理由を出力する。
secret_path() {
  local p="$1" base
  [[ -z "$p" ]] && return 1
  p="${p/#\~/$HOME}"
  p="${p/#\$HOME/$HOME}"
  p="${p/#\$\{HOME\}/$HOME}"
  base="${p##*/}"
  case "/$p/" in
    */.lab/* | */.ssh/* | */.kube/* | */.config/op/* | */.config/gh/* | */.docker/config.json/*)
      echo "資格情報の置き場所（$1）"; return 0 ;;
  esac
  case "$base" in
    .env.example | .env.sample | .env.template | .env.dist) return 1 ;;
    .env | .env.*) echo "環境変数ファイル（$1）"; return 0 ;;
    *.pem | *.key) echo "鍵ファイル（$1）"; return 0 ;;
  esac
  return 1
}

deny_path() {
  deny "$1 は読み取りを止めています。値が必要な作業は人に依頼し、値そのものは PR、Jira、ログに出さないでください。"
}

check_file_tools() {
  local k v why keys
  # Grep の pattern は正規表現なのでパスとして扱わない。
  case "$TOOL_NAME" in
    Read) keys="file_path" ;;
    Grep) keys="path glob" ;;
    Glob) keys="path pattern" ;;
  esac
  for k in $keys; do
    v="$(tool_input "$k")"
    why="$(secret_path "$v")" && deny_path "$why"
  done
  return 0
}

check_bash_segment() {
  local t="${WORDS[0]}" w why all=" ${WORDS[*]} "
  for w in "${WORDS[@]:1}"; do
    w="${w#*=}"  # --file=~/.ssh/id_ed25519 の形
    why="$(secret_path "$w")" && deny_path "$why"
  done
  case "$t" in
    printenv) deny "printenv は Secret を出力しうるため止めています。必要な変数名を指定して echo \"\${NAME:+set}\" で有無だけを確かめてください。" ;;
    env) ((${#WORDS[@]} == 1)) && deny "引数なしの env は Secret を出力しうるため止めています。" ;;
    op) [[ "${WORDS[1]:-}" == read || "${WORDS[1]:-} ${WORDS[2]:-}" == "item get" ]] &&
      deny "1Password からの値の取り出しは人が行います。" ;;
    gh) [[ "${WORDS[1]:-} ${WORDS[2]:-}" == "auth token" ]] && deny "gh auth token はトークンを出力するため止めています。" ;;
    argocd) [[ "$all" == *" admin initial-password "* ]] && deny "Argo CD の初期パスワードの表示は人が行います。" ;;
    kubectl)
      if [[ "$all" == *" get "* && "$all" =~ [\ ,]secrets?[\ ,/] ]]; then
        if [[ "$all" =~ \ (-o|--output)(\ +|=)?(yaml|json|jsonpath|go-template|template|custom-columns) ]]; then
          deny "Secret の値の表示（kubectl get secret -o ...）は止めています。一覧（kubectl get secret）か kubectl describe secret を使ってください。"
        fi
      fi ;;
  esac
  return 0
}

case "$TOOL_NAME" in
  Read | Grep | Glob) check_file_tools ;;
  Bash)
    CMD="$(tool_input command)"
    while IFS= read -r seg; do
      parse_words "$seg"
      ((${#WORDS[@]} == 0)) && continue
      check_bash_segment
    done < <(split_segments "$CMD")
    # リダイレクト（< ~/.lab/x）も見る。展開を止めてから空白で分ける。
    set -f
    for w in $CMD; do
      w="${w#<}"
      why="$(secret_path "$w")" && deny_path "$why"
    done
    set +f ;;
esac
exit 0
