#!/usr/bin/env bash
# cases.tsv の各行を hook の入力 JSON にして実行し、終了コードを照合する。
# 使い方: bash plugins/platform-lab/hooks/tests/run.sh
# kubectl は試験用のダミーに差し替える（現在の context を環境変数で返す）。
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
HOOKS="$(dirname "$HERE")"
FAKE_BIN="$(mktemp -d)"
trap 'rm -rf "$FAKE_BIN"' EXIT

cat >"$FAKE_BIN/kubectl" <<'EOF'
#!/usr/bin/env bash
if [[ "$1 $2" == "config current-context" ]]; then
  [[ -n "${FAKE_KUBE_CONTEXT:-}" ]] || { echo "error: current-context is not set" >&2; exit 1; }
  echo "$FAKE_KUBE_CONTEXT"; exit 0
fi
echo "fake kubectl: 試験中はクラスタに接続しません" >&2
exit 1
EOF
chmod +x "$FAKE_BIN/kubectl"

pass=0 fail=0 n=0
while IFS=$'\t' read -r hook tool input expect ctx branch; do
  [[ -z "$hook" || "$hook" == \#* ]] && continue
  n=$((n + 1))
  case "$tool" in
    Bash) key="command" ;;
    Read) key=file_path ;;
    Grep | Glob) key=path ;;
    *) echo "不明なツール: $tool" >&2; exit 1 ;;
  esac
  json="$(jq -cn --arg t "$tool" --arg k "$key" --arg v "$input" \
    '{hook_event_name: "PreToolUse", tool_name: $t, tool_input: {($k): $v}, cwd: "/tmp"}')"
  [[ "$ctx" == - ]] && ctx=""
  [[ "$branch" == - ]] && branch="feat/PLAT-0-test"
  err="$(PATH="$FAKE_BIN:$PATH" FAKE_KUBE_CONTEXT="$ctx" PLATFORM_LAB_TEST_BRANCH="$branch" \
    HOME=/home/u bash "$HOOKS/$hook.sh" <<<"$json" 2>&1 >/dev/null)"
  code=$?
  case "$expect" in allow) want=0 ;; deny) want=2 ;; *) want="$expect" ;; esac
  if [[ "$code" == "$want" ]]; then
    pass=$((pass + 1))
    printf 'ok   %-18s %-5s %s\n' "$hook" "$expect" "$input"
  else
    fail=$((fail + 1))
    printf 'FAIL %-18s want=%s got=%s %s\n     %s\n' "$hook" "$want" "$code" "$input" "$err"
  fi
done <"$HERE/cases.tsv"

echo "---"
echo "$n 件中 $pass 件合格、$fail 件不合格"
[[ "$fail" == 0 ]]
