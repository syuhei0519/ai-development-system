#!/usr/bin/env bash
# Edit / Write の後に、編集したファイルの種類に応じた lint を実行する（03 の「各 hook の判定規則」）。
# 拒否はしない。問題があれば終了コード 2 で内容を Claude に返す。ツールがなければ何もしない。
set -uo pipefail
HOOK_NAME=post-edit-lint
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
command -v jq >/dev/null 2>&1 || exit 0
read_input
FILE="$(tool_input file_path)"
[[ -n "$FILE" ]] || exit 0
[[ "$FILE" == /* ]] || FILE="${HOOK_CWD:-.}/$FILE"
[[ -f "$FILE" ]] || exit 0
DIR="$(dirname "$FILE")"

has() { command -v "$1" >/dev/null 2>&1; }

# 上の階層へたどって、名前 $1 のファイルがあるディレクトリを返す。
find_up() {
  local d="$DIR"
  while [[ "$d" != / && "$d" != . ]]; do
    [[ -e "$d/$1" ]] && { printf '%s\n' "$d"; return 0; }
    d="$(dirname "$d")"
  done
  return 1
}

report() {
  printf '[platform-lab/%s] %s で問題が見つかりました（%s）。直してから次に進んでください。\n' \
    "$HOOK_NAME" "$1" "${FILE#"${HOOK_CWD:-}"/}" >&2
  head -n 40 <<<"$2" >&2
  exit 2
}

case "$FILE" in
  *.go)
    has gofmt || exit 0
    out="$(gofmt -l "$FILE" 2>&1)"
    [[ -z "$out" ]] || report "gofmt -l" "gofmt -w で整形が必要です: $out" ;;
  *.sh | *.bash)
    has shellcheck || exit 0
    out="$(cd "$DIR" && shellcheck -x "$(basename "$FILE")" 2>&1)" || report shellcheck "$out" ;;
  *.js | *.jsx | *.ts | *.tsx | *.mjs | *.cjs)
    root="$(find_up package.json)" || exit 0
    lint="$root/node_modules/.bin/eslint"
    [[ -x "$lint" ]] || { has eslint && lint=eslint; } || exit 0
    out="$(cd "$root" && "$lint" --no-warn-ignored "$FILE" 2>&1)"
    # 終了コード 1 が指摘あり。2 は設定がないなどの実行エラーなので扱わない。
    [[ $? -eq 1 ]] && report eslint "$out" ;;
  *.yaml | *.yml | *.tpl)
    if chart="$(find_up Chart.yaml)"; then
      has helm || exit 0
      out="$(helm lint "$chart" 2>&1)" || report "helm lint" "$out"
    elif [[ "$FILE" != *.tpl ]] && has yamllint; then
      out="$(yamllint -f parsable "$FILE" 2>&1)" || report yamllint "$out"
    fi ;;
esac
exit 0
