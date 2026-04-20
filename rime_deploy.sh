#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/export/rime/rime-teochew"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: source directory not found: $SOURCE_DIR"
    echo "Run build.sh first to generate Rime files."
    exit 1
fi

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

for file in "$SOURCE_DIR"/*; do
    [ -f "$file" ] || continue
    cp -v "$file" "$target/"
done

if [ -d "$SOURCE_DIR/lua" ]; then
    mkdir -p "$target/lua"
    for file in "$SOURCE_DIR/lua"/*; do
        [ -f "$file" ] || continue
        cp -v "$file" "$target/lua/"
    done
fi

echo ""
echo "Files copied successfully."
echo "Please open your input method menu and click \"Deploy\" (重新部署) to apply changes."
