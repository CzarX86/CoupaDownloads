#!/bin/bash

# Script to commit and push changes to main branch

echo "Checking git status..."
git status

echo "Adding all changes to staging..."
git add .

echo "Committing changes..."
git commit -m "Comprehensive project update: Refactor core modules, add SPA interface, enhance documentation, and implement new features

- Refactored core downloader and processor modules for improved reliability
- Added new SPA (Single Page Application) interface for PDF training
- Implemented server-side components for database and API management
- Enhanced documentation with AGENTS.md workflow guidelines
- Added new tools for LLM critique, PDF annotation, and training wizards
- Removed legacy files and consolidated PR_PLANS structure
- Updated dependencies and configuration files
- Integrated new testing suites and performance improvements"

echo "Switching to main branch..."
git checkout main

echo "Merging changes from chore/full-source-commit-2025-09-16 to main..."
git merge chore/full-source-commit-2025-09-16

echo "Pushing to main branch..."
git push origin main

echo "Process completed!"