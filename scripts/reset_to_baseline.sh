#!/usr/bin/env bash
set -euo pipefail

# Reset to baseline (destructive)
# USAGE: review the script, then run: bash scripts/reset_to_baseline.sh
# THIS WILL: close open PRs, create an orphan commit from current workspace,
# force-push it to 'main', and delete other remote branches.

# Ensure running from repository root (script assumes repository root path)
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PWD=$(pwd)
echo "Repository root: $PWD"

# Check for GitHub CLI
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI 'gh' not found in PATH. Install and authenticate first: https://cli.github.com/"
  exit 2
fi

# Show remotes
git remote -v

echo "Listing open PRs (if any):"
gh pr list --state open --json number,title,headRefName || true

read -p "Proceed to CLOSE all open PRs and perform destructive reset? (type YES to continue) " confirm
if [ "$confirm" != "YES" ]; then
  echo "Aborted by user."; exit 1
fi

# Close open PRs and delete their branches
pr_numbers=$(gh pr list --state open --json number -q '.[].number' || true)
if [ -n "$pr_numbers" ]; then
  echo "Closing open PRs..."
  echo "$pr_numbers" | xargs -r -n1 -I % sh -c 'echo "Closing PR #%"; gh pr close % --delete-branch || true'
else
  echo "No open PRs to close."
fi

# Create orphan branch from current working tree
echo "Creating orphan branch 'baseline-clean' from current workspace..."
# preserve index (staged changes) and include uncommitted changes
git checkout --orphan baseline-clean
git add -A
if git diff --staged --quiet; then
  git commit --allow-empty -m "Baseline: fresh start from current state (reset by script)"
else
  git commit -m "Baseline: fresh start from current state (reset by script)"
fi

# Rename to main and force push
git branch -M baseline-clean main
echo "Force pushing 'main' to origin..."
git push --force origin main

# Delete other remote branches
echo "Pruning and deleting other remote branches (except 'main')..."
git fetch --prune
other_branches=$(git for-each-ref --format='%(refname:short)' refs/remotes/origin | sed 's|origin/||' | grep -v '^main$' | grep -v '->' || true)
if [ -n "$other_branches" ]; then
  echo "$other_branches" | while read -r b; do
    echo "Deleting origin/$b"
    git push origin --delete "$b" || true
  done
else
  echo "No other remote branches to delete."
fi

# Set default branch on GitHub to main
echo "Setting default branch on GitHub to 'main' (if permitted)..."
gh repo edit --default-branch main || true

cat <<EOF
Destructive reset complete.
- The remote default branch is now 'main' and contains a fresh initial commit with the current workspace snapshot.
- All open PRs were closed and (most) remote branches were deleted.
IMPORTANT: All collaborators must re-clone the repository:
  git clone <repo-url>
EOF
