Reset to baseline — instructions

Overview

This repository contains a destructive reset script at `scripts/reset_to_baseline.sh`.
Running this script will:
- Close all open PRs (using GitHub CLI `gh`).
- Create an orphan commit from the current working tree and set it as `main`.
- Force-push the new `main` to `origin`.
- Delete other remote branches.
- Attempt to set the default branch on GitHub to `main`.

Before you run

1. Ensure you have `gh` installed and authenticated: https://cli.github.com/
2. Pull any local uncommitted changes you want included — the script will include uncommitted files when creating the orphan commit.
3. Notify collaborators: this will rewrite remote history and delete branches. They must re-clone after the reset.

How to run

```bash
# make script executable
chmod +x scripts/reset_to_baseline.sh
# run it
bash scripts/reset_to_baseline.sh
```

If you prefer, review the script and run commands manually instead of the packaged script.
