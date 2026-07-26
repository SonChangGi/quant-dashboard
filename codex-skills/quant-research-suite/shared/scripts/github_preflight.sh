#!/usr/bin/env bash
set -euo pipefail
shopt -s nocasematch

project_root="${1:-}"
expected_repo="${2:-}"
expected_account="${3:-}"
require_write="${4:-true}"

if [[ -z "$project_root" || -z "$expected_repo" || -z "$expected_account" ]]; then
  echo "BLOCKED: usage: github_preflight.sh PROJECT_ROOT OWNER/REPO ACCOUNT [true|false]" >&2
  exit 2
fi

if [[ "$require_write" != "true" && "$require_write" != "false" ]]; then
  echo "BLOCKED: require_write must be true or false." >&2
  exit 2
fi

if ! command -v git >/dev/null 2>&1; then
  echo "BLOCKED: git is not installed." >&2
  exit 2
fi

if ! git -C "$project_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "BLOCKED: not a git worktree: $project_root" >&2
  exit 2
fi

remote_url="$(git -C "$project_root" remote get-url origin 2>/dev/null || true)"
if [[ -z "$remote_url" ]]; then
  echo "BLOCKED: origin remote is missing." >&2
  exit 2
fi

safe_remote_url="$remote_url"
if [[ "$safe_remote_url" =~ ^(https?://)[^/@]+@(.+)$ ]]; then
  safe_remote_url="${BASH_REMATCH[1]}${BASH_REMATCH[2]}"
fi

repo_slug=""
case "$safe_remote_url" in
  https://github.com/*)
    repo_slug="${safe_remote_url#https://github.com/}"
    ;;
  git@github.com:*)
    repo_slug="${safe_remote_url#git@github.com:}"
    ;;
esac
repo_slug="${repo_slug%.git}"
if [[ -z "$repo_slug" || "$repo_slug" != */* ]]; then
  echo "BLOCKED: origin is not a recognized GitHub repository URL." >&2
  exit 2
fi

branch="$(git -C "$project_root" branch --show-current)"
head_sha="$(git -C "$project_root" rev-parse HEAD)"
status="$(git -C "$project_root" status --short)"
if [[ -z "$branch" ]]; then
  echo "BLOCKED: detached HEAD cannot be used for release." >&2
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "BLOCKED: GitHub CLI (gh) is not installed." >&2
  exit 3
fi

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  echo "BLOCKED: GitHub authentication is unavailable in this execution context." >&2
  echo "Reauthenticate through the user-approved GitHub flow, then rerun preflight." >&2
  exit 4
fi

account="$(gh api user --jq .login 2>/dev/null || true)"
repo_name="$(gh repo view "$repo_slug" --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)"
default_branch="$(gh repo view "$repo_slug" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null || true)"
push_permission="$(gh api "repos/$repo_slug" --jq '.permissions.push // false' 2>/dev/null || true)"

if [[ -z "$account" || -z "$repo_name" || -z "$default_branch" ]]; then
  echo "BLOCKED: authenticated account cannot read the repository." >&2
  exit 5
fi

if [[ "$repo_name" != "$repo_slug" ]]; then
  echo "BLOCKED: origin and authenticated repository identity differ." >&2
  exit 5
fi

if [[ "$repo_name" != "$expected_repo" ]]; then
  echo "BLOCKED: repository differs from the approved target." >&2
  exit 5
fi

if [[ "$account" != "$expected_account" ]]; then
  echo "BLOCKED: authenticated account differs from the approved account." >&2
  exit 5
fi

if [[ "$require_write" == "true" && "$push_permission" != "true" ]]; then
  echo "BLOCKED: authenticated account lacks repository push permission." >&2
  exit 5
fi

if ! git -C "$project_root" ls-remote --exit-code origin HEAD >/dev/null 2>&1; then
  echo "BLOCKED: origin is not reachable with current credentials/network." >&2
  exit 6
fi

upstream="$(git -C "$project_root" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
ahead=""
behind=""
if [[ -n "$upstream" ]]; then
  divergence="$(git -C "$project_root" rev-list --left-right --count "$upstream...HEAD" 2>/dev/null || true)"
  if [[ "$divergence" =~ ^([0-9]+)[[:space:]]+([0-9]+)$ ]]; then
    behind="${BASH_REMATCH[1]}"
    ahead="${BASH_REMATCH[2]}"
  fi
fi

echo "GitHub preflight passed"
echo "account=$account"
echo "repository=$repo_name"
echo "remote=$safe_remote_url"
echo "branch=${branch:-DETACHED}"
echo "default_branch=${default_branch:-unknown}"
echo "head=$head_sha"
echo "push_permission=${push_permission:-unknown}"
echo "upstream=${upstream:-none}"
echo "ahead=${ahead:-unknown}"
echo "behind=${behind:-unknown}"
if [[ -n "$status" ]]; then
  echo "worktree=dirty"
else
  echo "worktree=clean"
fi
