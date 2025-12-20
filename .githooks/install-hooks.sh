#!/bin/sh
# .githooks/install-hooks.sh
# install Git hooks for Loom project

echo "installing Git hooks for Loom..."

# * check if in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ not a git repository. please run this script from the root of your git repository."
    exit 1
fi

# * check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml not found. this script is designed for Python projects using pyproject.toml."
    exit 1
fi

# config Git to use .githooks directory
if ! git config core.hooksPath .githooks; then
    echo "❌ failed to configure git hooks path"
    exit 1
fi

# verify hooks are executable
if [ ! -x ".githooks/pre-commit" ]; then
    echo "making pre-commit hook executable..."
    chmod +x .githooks/pre-commit
fi

if [ ! -x ".githooks/pre-push" ]; then
    echo "making pre-push hook executable..."
    chmod +x .githooks/pre-push
fi

echo "✅ Git hooks installed successfully!"
echo ""
echo "the following hooks are now active:"
echo "  - pre-commit: auto-versions pyproject.toml & CHANGELOG.md on nightly branch"
echo "  - pre-push: ensures CHANGELOG.md is updated when pushing to nightly branch"
echo ""
echo "🔧 hook behavior:"
echo "  - only activates on the 'nightly' branch"
echo "  - automatically increments version as X.Y.Z-nightly.YYYYMMDD"
echo "  - maintains version sync between pyproject.toml & CHANGELOG.md"
echo "  - requires CHANGELOG.md updates for nightly pushes"
echo ""
echo "to disable hooks temporarily, use:"
echo "  git commit --no-verify    # skip pre-commit hook"
echo "  git push --no-verify      # skip pre-push hook"