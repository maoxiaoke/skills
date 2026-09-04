#!/usr/bin/env bash
#
# sync-skills.sh — 把本项目里的技能(skills)以软链接方式同步到本地技能目录
#
# 项目布局: <类别>/<技能名>/SKILL.md  (类别如 going/others/owned/testing)
# 默认目标:  ~/.claude/skills/<技能名> -> /绝对路径/<类别>/<技能名>
#            ~/.agents/skills/<技能名> -> /绝对路径/<类别>/<技能名>
#
# 用法:
#   ./sync-skills.sh                  同步全部技能
#   ./sync-skills.sh <技能名>          只同步单个技能 (如: scrum)
#   ./sync-skills.sh <类别>/<技能名>   重名时精确指定 (如: going/grill-me)
#   ./sync-skills.sh -i               交互式:列出技能让你输入编号选择
#   ./sync-skills.sh --list           列出本项目发现的所有技能
#   ./sync-skills.sh --dry-run [...]  预演,不实际改动
#   ./sync-skills.sh --prune          清理目标目录中指向本项目但已失效的软链接
#   ./sync-skills.sh --force [...]    连「真实目录/文件」也覆盖(默认会跳过保护)
#   ./sync-skills.sh --target DIR     只同步到自定义目标目录(覆盖两个默认目标)
#   ./sync-skills.sh -h | --help      显示帮助
#
set -euo pipefail

# ---- 配置 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$SCRIPT_DIR"
TARGET_DIRS=(
  "${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
  "${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
)
EXCLUDE_DIRS=("docs" "node_modules" ".git")

# ---- 选项 ----
DRY_RUN=0
FORCE=0
DO_LIST=0
DO_PRUNE=0
INTERACTIVE=0
SELECTOR=""

# ---- 颜色/日志 ----
if [[ -t 1 ]]; then
  C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YEL=$'\033[33m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_DIM=""; C_RST=""
fi
info() { printf '%s\n' "$*"; }
ok()   { printf '%s✓%s %s\n' "$C_GRN" "$C_RST" "$*"; }
warn() { printf '%s!%s %s\n' "$C_YEL" "$C_RST" "$*" >&2; }
err()  { printf '%s✗%s %s\n' "$C_RED" "$C_RST" "$*" >&2; }
die()  { err "$*"; exit 1; }
run()  { if [[ $DRY_RUN -eq 1 ]]; then printf '%s[dry-run]%s %s\n' "$C_DIM" "$C_RST" "$*"; else eval "$*"; fi; }

usage() { sed -n '3,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

# ---- 参数解析 ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --list)    DO_LIST=1; shift ;;
    -i|--interactive) INTERACTIVE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --force)   FORCE=1; shift ;;
    --prune)   DO_PRUNE=1; shift ;;
    --target)  TARGET_DIRS=("${2:?--target 需要一个目录参数}"); shift 2 ;;
    --target=*) TARGET_DIRS=("${1#*=}"); shift ;;
    -*)        die "未知选项: $1 (用 --help 查看帮助)" ;;
    *)         [[ -n "$SELECTOR" ]] && die "一次只能指定一个技能,已有: $SELECTOR"; SELECTOR="$1"; shift ;;
  esac
done

# ---- 发现技能: 填充 name -> "rel_path" (可能多条,用于检测重名) ----
# 兼容老 bash(3.x,macOS 自带),不用关联数组,用并行普通数组。
NAMES=()    # 技能名
PATHS=()    # 相对项目根的路径 (如 going/scrum)

is_excluded() {
  local p="$1" ex
  for ex in "${EXCLUDE_DIRS[@]}"; do
    [[ "$p" == "$ex"/* || "$p" == "$ex" ]] && return 0
  done
  return 1
}

discover() {
  local skill_md rel dir name
  while IFS= read -r skill_md; do
    rel="${skill_md#"$SOURCE_ROOT"/}"   # 类别/技能/SKILL.md
    dir="$(dirname "$rel")"             # 类别/技能
    is_excluded "$dir" && continue
    name="$(basename "$dir")"
    NAMES+=("$name")
    PATHS+=("$dir")
  done < <(find "$SOURCE_ROOT" -maxdepth 3 -name SKILL.md -type f | sort)
}

# 在已发现列表中按选择器(技能名 或 类别/技能名)解析出唯一相对路径,失败则退出
resolve_one() {
  local sel="$1" i matches=()
  for i in "${!NAMES[@]}"; do
    if [[ "$sel" == */* ]]; then
      [[ "${PATHS[$i]}" == "$sel" ]] && matches+=("${PATHS[$i]}")
    else
      [[ "${NAMES[$i]}" == "$sel" ]] && matches+=("${PATHS[$i]}")
    fi
  done
  if [[ ${#matches[@]} -eq 0 ]]; then
    die "未找到技能: $sel (用 --list 查看可用技能)"
  elif [[ ${#matches[@]} -gt 1 ]]; then
    err "技能名 '$sel' 重名,请用 类别/技能名 精确指定其一:"
    printf '    %s\n' "${matches[@]}" >&2
    exit 1
  fi
  printf '%s' "${matches[0]}"
}

# ---- 交互式选择: 列出技能让用户输入编号,把结果写入全局 PICKED ----
# PICKED 取值: "ALL"(全部) 或 某个相对路径(类别/技能名)
PICKED=""
pick_interactive() {
  local i choice
  info "选择要同步的技能 (目标: ${TARGET_DIRS[*]}):"
  printf '   %2s) %s\n' "0" "全部技能"
  for i in "${!NAMES[@]}"; do
    printf '   %2s) %-24s %s%s%s\n' "$((i+1))" "${NAMES[$i]}" "$C_DIM" "${PATHS[$i]}" "$C_RST"
  done
  while true; do
    printf '请输入编号 [0-%d] (q 退出): ' "${#NAMES[@]}"
    read -r choice || { echo; die "已取消"; }
    case "$choice" in
      q|Q) die "已取消" ;;
      0)   PICKED="ALL"; return 0 ;;
      ''|*[!0-9]*) warn "请输入数字"; continue ;;
      *)
        if (( choice >= 1 && choice <= ${#NAMES[@]} )); then
          PICKED="${PATHS[$((choice-1))]}"; return 0
        fi
        warn "超出范围: $choice" ;;
    esac
  done
}

# ---- 同步单个技能: 入参为相对路径 (类别/技能名) ----
link_skill() {
  local rel="$1"
  local target_dir="$2"
  local name; name="$(basename "$rel")"
  local src="$SOURCE_ROOT/$rel"          # 绝对源路径
  local dst="$target_dir/$name"          # 目标软链接

  if [[ -L "$dst" ]]; then
    local cur; cur="$(readlink "$dst")"
    if [[ "$cur" == "$src" ]]; then
      info "${C_DIM}= $name 在 $target_dir 中已是最新${C_RST}"; return 0
    fi
    run "rm '$dst'"
    run "ln -s '$src' '$dst'"
    ok "$name 已更新到 $target_dir ${C_DIM}(原 -> $cur)${C_RST}"
  elif [[ -e "$dst" ]]; then
    if [[ $FORCE -eq 1 ]]; then
      run "rm -rf '$dst'"
      run "ln -s '$src' '$dst'"
      ok "$name 已覆盖 $target_dir 中的真实目录/文件 (--force)"
    else
      warn "$name 目标是真实目录/文件,已跳过 (加 --force 覆盖): $dst"
      return 0
    fi
  else
    run "ln -s '$src' '$dst'"
    ok "$name 已链接到 $target_dir ${C_DIM}-> $rel${C_RST}"
  fi
}

# ---- 清理: 删除目标目录中指向本项目、但目标已不存在的软链接 ----
prune() {
  local target_dir="$1"
  local entry target
  [[ -d "$target_dir" ]] || return 0
  for entry in "$target_dir"/*; do
    [[ -L "$entry" ]] || continue
    target="$(readlink "$entry")"
    [[ "$target" == "$SOURCE_ROOT"/* ]] || continue   # 只管指向本项目的
    if [[ ! -e "$target" ]]; then
      run "rm '$entry'"
      ok "已清理失效软链接: $(basename "$entry") ${C_DIM}(原 -> $target)${C_RST}"
    fi
  done
}

# ================== 主流程 ==================
[[ -d "$SOURCE_ROOT" ]] || die "源目录不存在: $SOURCE_ROOT"
discover
[[ ${#NAMES[@]} -gt 0 ]] || die "在 $SOURCE_ROOT 下没有发现任何技能(含 SKILL.md 的目录)"

if [[ $DO_LIST -eq 1 ]]; then
  info "在 $SOURCE_ROOT 发现 ${#NAMES[@]} 个技能:"
  for i in "${!NAMES[@]}"; do
    printf '  %-24s %s%s%s\n' "${NAMES[$i]}" "$C_DIM" "${PATHS[$i]}" "$C_RST"
  done
  exit 0
fi

# 确保目标目录存在
for target_dir in "${TARGET_DIRS[@]}"; do
  if [[ ! -d "$target_dir" ]]; then
    run "mkdir -p '$target_dir'"
  fi
done

if [[ $DO_PRUNE -eq 1 ]]; then
  for target_dir in "${TARGET_DIRS[@]}"; do
    info "清理 $target_dir 中指向本项目的失效软链接..."
    prune "$target_dir"
  done
  [[ -z "$SELECTOR" ]] && exit 0   # 仅 --prune
fi

# 不带技能名、且在交互式终端运行时,默认弹出选择菜单(可用 -i 强制)
if [[ -z "$SELECTOR" && ( $INTERACTIVE -eq 1 || -t 0 ) ]]; then
  pick_interactive
  [[ "$PICKED" != "ALL" ]] && SELECTOR="$PICKED"
fi

if [[ -n "$SELECTOR" ]]; then
  # 单个同步
  rel="$(resolve_one "$SELECTOR")"
  for target_dir in "${TARGET_DIRS[@]}"; do
    link_skill "$rel" "$target_dir"
  done
else
  # 全部同步: 先检测重名,避免一个名字覆盖另一个
  declare -a seen_names=() dup=()
  for i in "${!NAMES[@]}"; do
    n="${NAMES[$i]}"
    for s in "${seen_names[@]:-}"; do [[ "$s" == "$n" ]] && dup+=("$n"); done
    seen_names+=("$n")
  done
  if [[ ${#dup[@]} -gt 0 ]]; then
    err "发现重名技能,无法在目标技能目录中共存。请用「类别/技能名」单独同步其一:"
    for i in "${!NAMES[@]}"; do
      for d in "${dup[@]}"; do
        [[ "${NAMES[$i]}" == "$d" ]] && printf '    %s\n' "${PATHS[$i]}" >&2
      done
    done
    die "解决重名后重试(例: ./sync-skills.sh going/grill-me)"
  fi
  info "同步全部 ${#NAMES[@]} 个技能到 ${TARGET_DIRS[*]} ..."
  for target_dir in "${TARGET_DIRS[@]}"; do
    for i in "${!NAMES[@]}"; do
      link_skill "${PATHS[$i]}" "$target_dir"
    done
  done
fi

ok "完成。"
