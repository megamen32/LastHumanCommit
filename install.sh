#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VERSION=$(sed -n '1p' "$ROOT/VERSION")
BEGIN='<!-- last-human-commit:begin -->'
END='<!-- last-human-commit:end -->'

fail() { printf '%s\n' "last-human-commit: $*" >&2; exit 1; }

usage() {
    cat <<'EOF'
Usage:
  install.sh host [all|codex|claude|opencode] [--dry-run]
  install.sh project [PATH] [--dry-run]
  install.sh status host|project [PATH]
  install.sh uninstall host|project [PATH]
EOF
}

is_target() {
    path=$1
    if [ -L "$path" ]; then fail "refusing symlink: $path"; fi
    if [ -e "$path" ] && [ ! -f "$path" ]; then fail "refusing non-file: $path"; fi
}

render() {
    template=$1
    root=$2
    awk -v root="$root" '
    {
        line = $0
        token = "@CANON_ROOT@"
        while ((pos = index(line, token)) > 0)
            line = substr(line, 1, pos - 1) root substr(line, pos + length(token))
        print line
    }' "$template"
}

preflight_entry() {
    path=$1
    is_target "$path"
    if [ -f "$path" ]; then
        begin=$(grep -cF "$BEGIN" "$path" || true)
        end=$(grep -cF "$END" "$path" || true)
        [ "$begin" -eq "$end" ] || fail "malformed markers: $path"
        [ "$begin" -le 1 ] || fail "duplicate markers: $path"
    fi
}

update_entry() {
    path=$1
    content=$2
    parent=$(dirname -- "$path")
    mkdir -p "$parent"
    if [ "${DRY_RUN:-0}" = 1 ]; then
        printf 'would update %s\n' "$path"
        return
    fi
    tmp="$path.tmp.$$"
    if [ -f "$path" ]; then
        begin=$(grep -cF "$BEGIN" "$path" || true)
        if [ "$begin" -eq 1 ]; then
            awk -v begin="$BEGIN" -v end="$END" -v block="$content" '
            $0 == begin { print; print_block=1; next }
            print_block && $0 == end { print block; print; print_block=0; next }
            !print_block { print }
            ' "$path" > "$tmp"
        else
            cp "$path" "$tmp"
            printf '\n%s\n%s\n%s\n' "$BEGIN" "$content" "$END" >> "$tmp"
        fi
    else
        printf '%s\n%s\n%s\n' "$BEGIN" "$content" "$END" > "$tmp"
    fi
    mv "$tmp" "$path"
}

copy_common() {
    destination=$1
    mkdir -p "$destination"
    cp -R "$ROOT/src/common/." "$destination/"
}

host_root() {
    printf '%s\n' "${XDG_DATA_HOME:-$HOME/.local/share}/last-human-commit/versions/$VERSION"
}

host_install() {
    target=${1:-all}
    dry=${2:-}
    [ "$target" = all ] || [ "$target" = codex ] || [ "$target" = claude ] || [ "$target" = opencode ] || fail "unknown host target: $target"
    [ "$dry" = --dry-run ] && DRY_RUN=1 || DRY_RUN=0
    data=$(host_root)
    common="$data/common"
    codex="${CODEX_HOME:-$HOME/.codex}/AGENTS.md"
    claude="$HOME/.claude/CLAUDE.md"
    opencode="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/AGENTS.md"
    [ "$target" = all ] || [ "$target" = codex ] && preflight_entry "$codex"
    [ "$target" = all ] || [ "$target" = claude ] && preflight_entry "$claude"
    [ "$target" = all ] || [ "$target" = opencode ] && preflight_entry "$opencode"
    if [ "$DRY_RUN" = 0 ]; then
        mkdir -p "$data"
        copy_common "$common"
        printf '%s\n' "$VERSION" > "$data/VERSION"
    fi
    block=$(mktemp)
    render "$ROOT/src/global/entry.md.in" "$common" > "$block"
    [ "$target" = all ] || [ "$target" = codex ] && update_entry "$codex" "$(cat "$block")"
    [ "$target" = all ] || [ "$target" = claude ] && update_entry "$claude" "$(cat "$block")"
    [ "$target" = all ] || [ "$target" = opencode ] && update_entry "$opencode" "$(cat "$block")"
    rm -f "$block"
    printf 'installed host v%s (%s)\n' "$VERSION" "$target"
}

project_install() {
    project=${1:-.}
    dry=${2:-}
    project=$(CDPATH= cd -- "$project" && pwd)
    [ "$dry" = --dry-run ] && DRY_RUN=1 || DRY_RUN=0
    preflight_entry "$project/AGENTS.md"
    preflight_entry "$project/CLAUDE.md"
    common="$project/.last-human-commit/common"
    if [ "$DRY_RUN" = 0 ]; then
        mkdir -p "$project/.last-human-commit"
        copy_common "$common"
        printf '%s\n' "$VERSION" > "$project/.last-human-commit/VERSION"
        if [ ! -e "$project/ROADMAP.md" ]; then
            cp "$ROOT/src/project/ROADMAP.md" "$project/ROADMAP.md"
        fi
    fi
    block=$(mktemp)
    render "$ROOT/src/project/entry.md.in" '.last-human-commit/common' > "$block"
    update_entry "$project/AGENTS.md" "$(cat "$block")"
    update_entry "$project/CLAUDE.md" "$(cat "$block")"
    rm -f "$block"
    printf 'installed project v%s: %s\n' "$VERSION" "$project"
}

status() {
    scope=$1
    path=${2:-.}
    if [ "$scope" = project ]; then
        for file in "$path/AGENTS.md" "$path/CLAUDE.md"; do
            if [ -f "$file" ] && grep -qF "$BEGIN" "$file"; then printf 'active %s\n' "$file"; else printf 'absent %s\n' "$file"; fi
        done
    else
        printf 'host payload: %s\n' "$(host_root)"
    fi
}

uninstall() {
    scope=$1
    path=${2:-.}
    [ "$scope" = project ] || fail 'host uninstall is not destructive; remove host marker files manually'
    preflight_entry "$path/AGENTS.md"
    preflight_entry "$path/CLAUDE.md"
    for file in "$path/AGENTS.md" "$path/CLAUDE.md"; do
        [ -f "$file" ] || continue
        tmp="$file.tmp.$$"
        awk -v begin="$BEGIN" -v end="$END" '
        $0 == begin { skip=1; next }
        skip && $0 == end { skip=0; next }
        !skip { print }
        ' "$file" > "$tmp"
        mv "$tmp" "$file"
    done
    printf 'removed managed project blocks; payload retained: %s/.last-human-commit\n' "$path"
}

[ "$#" -gt 0 ] || { usage; exit 2; }
case "$1" in
    host) shift; host_install "${1:-all}" "${2:-}" ;;
    project) shift; project_install "${1:-.}" "${2:-}" ;;
    status) shift; status "${1:-}" "${2:-.}" ;;
    uninstall) shift; uninstall "${1:-}" "${2:-.}" ;;
    *) usage; exit 2 ;;
esac
