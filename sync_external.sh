#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

EXTERNAL_DIR="external"

sync_repo() {
    local name="$1"
    local repo="$2"
    local branch="${3:-main}"
    local target="$EXTERNAL_DIR/$name"

    if [ -d "$target" ]; then
        echo "[$name] Already exists, skipping. Remove $target to re-sync."
        return
    fi

    echo "[$name] Cloning $repo ($branch)..."
    git clone --depth 1 --branch "$branch" "https://github.com/$repo.git" "$target"

    cd "$target"
    local commit
    commit=$(git rev-parse HEAD)
    local date
    date=$(git log -1 --format=%cs)
    echo "  Commit: $commit ($date)"
    cd - > /dev/null

    rm -rf "$target/.git"
    echo "[$name] Done."
}

sync_repo ChhoeTaigiDatabase ChhoeTaigi/ChhoeTaigiDatabase master
sync_repo dieghv kahaani/dieghv master
