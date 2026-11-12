#!/usr/bin/env bash
# main への push、強制 push、命名規則に合わない push、merge、
# リポジトリ設定と Secret の変更を止める。判定規則は 03 の「各 hook の判定規則」。
set -uo pipefail
HOOK_NAME=guard-git
# shellcheck source-path=SCRIPTDIR source=lib.sh
. "$(dirname "$0")/lib.sh"
require_jq
read_input
[[ "$TOOL_NAME" == Bash ]] || exit 0
CMD="$(tool_input command)"

BRANCH_RE='^(feat|fix|chore|docs)/PLAT-[0-9]+-[a-z0-9-]+$'
BUMP_RE='^chore/bump-[A-Za-z0-9._/-]+$'

current_branch() {
  if [[ -n "${PLATFORM_LAB_TEST_BRANCH:-}" ]]; then
    printf '%s\n' "$PLATFORM_LAB_TEST_BRANCH"; return
  fi
  git -C "${HOOK_CWD:-.}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo ""
}

check_dest() {
  local dst="${1#refs/heads/}"
  [[ "$dst" == HEAD ]] && dst="$(current_branch)"
  case "$dst" in
    main | master)
      deny "main への push は止めています（宛先: $dst）。作業ブランチ feat/PLAT-xxx-名前 に push して PR を作ってください。" ;;
    refs/tags/*)
      deny "タグの push は人が行います（$dst）。必要なコマンドを人に伝えてください。" ;;
  esac
  [[ "$dst" =~ $BRANCH_RE || "$dst" =~ $BUMP_RE ]] ||
    deny "ブランチ名「$dst」が規則 feat|fix|chore|docs/PLAT-番号-短い名前 に合いません。git switch -c で名前を付け直してから push してください。"
}

check_push() {
  local args=("$@") pos=() a k
  for ((k = 0; k < ${#args[@]}; k++)); do
    a="${args[k]}"
    case "$a" in
      -o | --push-option | --repo | --receive-pack | --exec) k=$((k + 1)) ;;
      --force-with-lease | --force-with-lease=* | --force-if-includes) ;;
      --force | -f) deny "強制 push は止めています。履歴を書き換えたい場合は --force-with-lease を使うか、人に確認してください。" ;;
      --delete | -d) deny "リモートのブランチやタグの削除は人が行います。" ;;
      --mirror | --all | --tags | --prune) deny "$a 付きの push は範囲が広すぎるため止めています。ブランチを 1 つ指定してください。" ;;
      --repo=* | --push-option=* | --receive-pack=* | --exec=* | -o*) ;;
      --*) ;;
      -*)
        [[ "$a" == *f* ]] && deny "強制 push（$a）は止めています。"
        [[ "$a" == *d* ]] && deny "リモートの削除（$a）は人が行います。" ;;
      *) pos+=("$a") ;;
    esac
  done
  # pos[0] はリモート名。refspec がなければ現在のブランチが宛先になる。
  if ((${#pos[@]} <= 1)); then
    check_dest "$(current_branch)"; return
  fi
  local spec src dst
  for spec in "${pos[@]:1}"; do
    [[ "$spec" == +* ]] && deny "強制 push（refspec $spec）は止めています。"
    [[ "$spec" == :* ]] && deny "リモートの削除（refspec $spec）は人が行います。"
    src="${spec%%:*}"; dst="${spec#*:}"
    [[ "$spec" == *:* ]] || dst="$src"
    check_dest "$dst"
  done
}

check_git() {
  local i=1 sub
  # git -C dir や -c k=v などのグローバルオプションを飛ばす。
  while ((i < ${#WORDS[@]})); do
    case "${WORDS[i]}" in
      -C | -c | --git-dir | --work-tree | --namespace) i=$((i + 2)) ;;
      -*) i=$((i + 1)) ;;
      *) break ;;
    esac
  done
  sub="${WORDS[i]:-}"
  local rest=("${WORDS[@]:i+1}")
  case "$sub" in
    push) check_push "${rest[@]}" ;;
    commit)
      case "$(current_branch)" in
        main | master) deny "main 上での commit は止めています。git switch -c feat/PLAT-xxx-名前 で作業ブランチを作ってください。" ;;
      esac ;;
    tag)
      local a
      for a in "${rest[@]}"; do
        [[ "$a" == -d || "$a" == --delete ]] && deny "タグの削除は人が行います。"
      done ;;
  esac
}

check_gh() {
  local sub="${WORDS[1]:-}" act="${WORDS[2]:-}" a method=GET path="" body=0
  case "$sub $act" in
    "pr merge") deny "PR の merge は人が行います。CI と AI レビューの結果を伝えて、merge を依頼してください。" ;;
    "repo delete") deny "リポジトリの削除は止めています。" ;;
    "variable set" | "variable delete") deny "GitHub の Variables の変更は人が行います。" ;;
    "ruleset "*) [[ "$act" == list || "$act" == view || "$act" == check ]] || deny "ruleset の変更は人が行います。" ;;
  esac
  [[ "$sub" == secret ]] && deny "GitHub の Secret の操作は人が行います。"
  [[ "$sub" == api ]] || return 0
  for ((j = 2; j < ${#WORDS[@]}; j++)); do
    a="${WORDS[j]}"
    case "$a" in
      -X | --method) method="${WORDS[j + 1]:-GET}"; j=$((j + 1)) ;;
      -X* | --method=*) method="${a#-X}"; method="${method#--method=}" ;;
      -f | -F | --field | --raw-field | --input) body=1; j=$((j + 1)) ;;
      -f* | -F* | --field=* | --raw-field=* | --input=*) body=1 ;;
      -*) ;;
      *) [[ -z "$path" ]] && path="$a" ;;
    esac
  done
  method="${method^^}"
  [[ "$method" == GET && "$body" == 1 ]] && method=POST
  [[ "$method" == DELETE ]] && deny "gh api の DELETE は止めています（$path）。人に確認してください。"
  if [[ "$path" =~ (rulesets|/protection|/environments|/actions/secrets|/actions/variables) && "$method" != GET ]]; then
    deny "リポジトリの保護設定や Secret の変更（$method $path）は人が行います。"
  fi
}

while IFS= read -r seg; do
  parse_words "$seg"
  ((${#WORDS[@]} == 0)) && continue
  case "${WORDS[0]}" in
    git) check_git ;;
    gh) check_gh ;;
  esac
done < <(split_segments "$CMD")
exit 0
