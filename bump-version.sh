#!/usr/bin/env bash
# 版本自增：./bump-version.sh [major|minor|patch]（默认 patch）
# 规则（2026-10-12 老板拍板）：每次改动都 bump，提交标题一律带 v<新版本>
set -euo pipefail
cd "$(dirname "$0")"
mode="${1:-patch}"
v="$(cat VERSION)"
IFS=. read -r major minor patch <<< "$v"
case "$mode" in
  major) major=$((major + 1)); minor=0; patch=0 ;;
  minor) minor=$((minor + 1)); patch=0 ;;
  patch) patch=$((patch + 1)) ;;
  *) echo "用法: $0 [major|minor|patch]" >&2; exit 1 ;;
esac
nv="$major.$minor.$patch"
echo "$nv" > VERSION
echo "v$nv"
