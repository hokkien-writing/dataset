#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIRS=(
    "$SCRIPT_DIR/export/rime/rime-hokkien"
    "$SCRIPT_DIR/export/rime/rime-teochew"
)

for d in "${SOURCE_DIRS[@]}"; do
    if [ ! -d "$d" ]; then
        echo "Error: source directory not found: $d"
        echo "Run build.sh first to generate Rime files."
        exit 1
    fi
done

detect_os() {
    local uname_out
    uname_out="$(uname -s)"
    case "$uname_out" in
        Darwin*)
            echo "mac"
            ;;
        Linux*)
            if grep -qi microsoft /proc/version 2>/dev/null; then
                echo "wsl"
            else
                echo "linux"
            fi
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

get_rime_target() {
    local os="$1"
    case "$os" in
        mac)
            echo "$HOME/Library/Rime"
            ;;
        wsl)
            local win_user
            win_user="$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')"
            if [ -z "$win_user" ]; then
                echo "Error: cannot determine Windows username" >&2
                exit 1
            fi
            echo "/mnt/c/Users/$win_user/AppData/Roaming/Rime"
            ;;
        *)
            return 1
            ;;
    esac
}

os="$(detect_os)"

if ! target="$(get_rime_target "$os")"; then
    echo "Error: unsupported OS. This script supports macOS and WSL on Windows."
    exit 1
fi

echo "Detected environment: $os"
echo "Target directory: $target"

mkdir -p "$target"

schema_lines=""
page_size=""
for SOURCE_DIR in "${SOURCE_DIRS[@]}"; do
    echo ""
    echo "Deploying: $(basename "$SOURCE_DIR")"

    for file in "$SOURCE_DIR"/*; do
        [ -f "$file" ] || continue
        fname="$(basename "$file")"
        case "$fname" in
            rime.lua)
                ;;
            default.custom.yaml)
                while IFS= read -r line; do
                    case "$line" in
                        "    - schema:"*)
                            schema_lines="$schema_lines
$line"
                            ;;
                        *"menu/page_size"*)
                            page_size="$line"
                            ;;
                    esac
                done < "$file"
                ;;
            *)
                cp -v "$file" "$target/"
                ;;
        esac
    done
done

cp -v "${SOURCE_DIRS[1]}/rime.lua" "$target/rime.lua"

mkdir -p "$target/lua"
for file in "${SOURCE_DIRS[1]}/lua"/*; do
    [ -f "$file" ] || continue
    cp -v "$file" "$target/lua/"
done

{
    echo "# Rime default settings customization"
    echo "# Generated from merged.csv - do not edit manually"
    echo ""
    echo "patch:"
    echo "  schema_list:"
    printf "%s\n" "$schema_lines" | sed '/^$/d' | sort -u
    echo "$page_size"
} > "$target/default.custom.yaml"
echo "Merged default.custom.yaml written to $target/default.custom.yaml"

echo ""
echo "Files copied successfully."
echo "Please open your input method menu and click \"Deploy\" (重新部署) to apply changes."
