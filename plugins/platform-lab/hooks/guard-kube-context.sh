#!/usr/bin/env bash
# kind-platform-lab 以外のクラスタへの操作を止める。
# 判定規則は 03 の「各 hook の判定規則」。確実な柵は専用 kubeconfig（P1-02）が受け持つ。
set -uo pipefail
HOOK_NAME=guard-kube-context
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_jq
read_input
[[ "$TOOL_NAME" == Bash ]] || exit 0
CMD="$(tool_input command)"

ALLOWED_CONTEXT="${PLATFORM_LAB_CONTEXT:-kind-platform-lab}"
ALLOWED_CLUSTER="${ALLOWED_CONTEXT#kind-}"
KUBE_TOOLS=" kubectl helm argocd k9s kubeseal "

# export KUBECONFIG=... のように前の文で差し替える形も止める。
if [[ "$CMD" == *KUBECONFIG=* && "$CMD" =~ (^|[^A-Za-z0-9_-])(kubectl|helm|argocd|k9s|kubeseal|kind)([^A-Za-z0-9_-]|$) ]]; then
  deny "KUBECONFIG の差し替えは止めています。専用の kubeconfig（$ALLOWED_CONTEXT だけを含む）をそのまま使ってください。"
fi

# クラスタに接続しないコマンドは context を問わず許可する。
offline() {
  local t="${WORDS[0]}" s="${WORDS[1]:-}" all=" ${WORDS[*]} "
  case "$t" in
    helm)
      case "$s" in lint | template | version | repo | dependency | dep | package | show | inspect | pull | fetch | create | search | env | completion | plugin | verify | help | --help | -h) return 0 ;; esac ;;
    kubectl)
      case "$s" in
        version) [[ "$all" == *" --client"* ]] && return 0 ;;
        kustomize | completion | explain | help | --help | -h) return 0 ;;
        config) case "${WORDS[2]:-}" in view | current-context | get-contexts | get-clusters) return 0 ;; esac ;;
      esac ;;
    argocd) [[ "$s" == version && "$all" == *" --client"* ]] && return 0 ;;
    kubeseal) [[ "$all" == *" --version "* || "$all" == *" --help "* ]] && return 0 ;;
  esac
  return 1
}

current_context() {
  local ctx
  ctx="$(kubectl config current-context 2>/dev/null)" || ctx=""
  printf '%s\n' "${ctx:-（なし）}"
}

check_kube() {
  local t="${WORDS[0]}" a ctx="" i
  for a in "${ENV_ASSIGNS[@]}"; do
    [[ "$a" == KUBECONFIG=* ]] &&
      deny "KUBECONFIG の差し替えは止めています。専用の kubeconfig（$ALLOWED_CONTEXT だけを含む）をそのまま使ってください。"
  done
  for ((i = 1; i < ${#WORDS[@]}; i++)); do
    a="${WORDS[i]}"
    case "$a" in
      --kubeconfig | --kubeconfig=*)
        deny "--kubeconfig の指定は止めています。専用の kubeconfig をそのまま使ってください。" ;;
      --context | --kube-context) ctx="${WORDS[i + 1]:-}"; i=$((i + 1)) ;;
      --context=* | --kube-context=*) ctx="${a#*=}" ;;
    esac
  done
  if [[ "$t" == kubectl && "${WORDS[1]:-}" == config ]]; then
    case "${WORDS[2]:-}" in
      use-context | set-context | set-cluster | set-credentials | delete-context | delete-cluster | rename-context)
        deny "kubeconfig の書き換え（kubectl config ${WORDS[2]}）は止めています。context は $ALLOWED_CONTEXT に固定です。" ;;
    esac
  fi
  if [[ -n "$ctx" ]]; then
    [[ "$ctx" == "$ALLOWED_CONTEXT" ]] && return 0
    deny "context が $ALLOWED_CONTEXT ではありません（指定: $ctx）。別クラスタの操作は人が行います。"
  fi
  offline && return 0
  local cur
  cur="$(current_context)"
  [[ "$cur" == "$ALLOWED_CONTEXT" ]] ||
    deny "context が $ALLOWED_CONTEXT ではありません（現在: $cur）。make up を実行するか、人に確認してください。"
}

check_kind() {
  local s="${WORDS[1]:-}" name="" i
  case "$s" in version | help | --help | -h | completion | "") return 0 ;; esac
  [[ "$s" == get && "${WORDS[2]:-}" == clusters ]] && return 0
  for ((i = 1; i < ${#WORDS[@]}; i++)); do
    case "${WORDS[i]}" in
      --name | -n) name="${WORDS[i + 1]:-}"; i=$((i + 1)) ;;
      --name=*) name="${WORDS[i]#--name=}" ;;
    esac
  done
  [[ "$name" == "$ALLOWED_CLUSTER" ]] ||
    deny "kind の操作対象が $ALLOWED_CLUSTER ではありません（--name: ${name:-未指定（既定は kind）}）。別クラスタの操作は人が行います。"
}

while IFS= read -r seg; do
  parse_words "$seg"
  ((${#WORDS[@]} == 0)) && continue
  if [[ "$KUBE_TOOLS" == *" ${WORDS[0]} "* ]]; then
    check_kube
  elif [[ "${WORDS[0]}" == kind ]]; then
    check_kind
  fi
done < <(split_segments "$CMD")
exit 0
