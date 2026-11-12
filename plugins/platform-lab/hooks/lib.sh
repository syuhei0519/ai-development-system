# shellcheck shell=bash disable=SC2034
# platform-lab の hook が共有する関数。各 hook から source する。
# hook は標準入力の JSON（tool_name、tool_input、cwd）を読み、
# 拒否するときは標準エラーに理由を書いて終了コード 2 を返す。

HOOK_NAME="${HOOK_NAME:-platform-lab}"

deny() {
  printf '[platform-lab/%s] %s\n' "$HOOK_NAME" "$*" >&2
  exit 2
}

# jq がない環境では判定できないため、安全側（拒否）に倒す。
require_jq() {
  command -v jq >/dev/null 2>&1 ||
    deny "jq が見つからないため判定できません。jq を入れてから再実行するか、人に確認してください。"
}

# 標準入力を一度だけ読み、INPUT_JSON に保持する。
read_input() {
  INPUT_JSON="$(cat)"
  TOOL_NAME="$(jq -r '.tool_name // ""' <<<"$INPUT_JSON")" ||
    deny "hook の入力 JSON を読めません。"
  HOOK_CWD="$(jq -r '.cwd // ""' <<<"$INPUT_JSON")"
}

tool_input() {
  jq -r --arg k "$1" '.tool_input[$k] // ""' <<<"$INPUT_JSON"
}

# Bash のコマンド文字列を、&&、||、;、|、改行、$( で区切った単純コマンドに分ける。
# 引用符の中は区切らない程度の簡易な分割で、完全な構文解析ではない。
# 迂回への備えは sandbox と専用 kubeconfig が受け持つ（03 の「柵の 4 層」）。
split_segments() {
  awk '
    {
      line = $0; out = ""; q = ""
      for (i = 1; i <= length(line); i++) {
        c = substr(line, i, 1); n = substr(line, i + 1, 1)
        if (q != "") { if (c == q) q = ""; out = out c; continue }
        if (c == "\"" || c == "\047") { q = c; out = out c; continue }
        if ((c == "&" && n == "&") || (c == "|" && n == "|")) { print out; out = ""; i++; continue }
        if (c == ";" || c == "|" || c == "&" || c == "(" || c == ")" || c == "`") { print out; out = ""; continue }
        if (c == "$" && n == "(") { print out; out = ""; i++; continue }
        out = out c
      }
      print out
    }' <<<"$1"
}

# 単純コマンド 1 つを単語の配列 WORDS に分ける。引用符は取り除く。
# 先頭の環境変数代入は ENV_ASSIGNS に、sudo / env / command / exec / time は飛ばす。
parse_words() {
  local seg="$1" w
  WORDS=(); ENV_ASSIGNS=()
  # xargs で引用符を解釈する。失敗したら空白で分ける。
  if ! mapfile -t WORDS < <(xargs -n1 printf '%s\n' <<<"$seg" 2>/dev/null); then
    read -ra WORDS <<<"$seg"
  fi
  while ((${#WORDS[@]} > 0)); do
    w="${WORDS[0]}"
    if [[ "$w" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      ENV_ASSIGNS+=("$w"); WORDS=("${WORDS[@]:1}")
    elif [[ "$w" == sudo || "$w" == command || "$w" == exec || "$w" == time || "$w" == nohup ]]; then
      WORDS=("${WORDS[@]:1}")
    elif [[ "$w" == env && ${#WORDS[@]} -gt 1 ]]; then
      WORDS=("${WORDS[@]:1}")
    else
      break
    fi
  done
  # /usr/bin/kubectl のような絶対パスは名前だけにする。
  if ((${#WORDS[@]} > 0)); then WORDS[0]="${WORDS[0]##*/}"; fi
}
