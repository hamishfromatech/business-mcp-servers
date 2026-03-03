#!/bin/bash
# Create Branch Helper
# Creates a branch with validated naming convention

echo "=== Branch Creator ==="
echo ""

# Prompt for branch type
echo "Select branch type:"
echo "  1) feature  - New feature"
echo "  2) fix      - Bug fix"
echo "  3) docs     - Documentation"
echo "  4) refactor - Code refactoring"
echo "  5) test     - Adding tests"
echo ""
read -p "Enter number (1-5): " type_num

case $type_num in
    1) PREFIX="feature" ;;
    2) PREFIX="fix" ;;
    3) PREFIX="docs" ;;
    4) PREFIX="refactor" ;;
    5) PREFIX="test" ;;
    *) echo "Invalid selection"; exit 1 ;;
esac

# Prompt for description
read -p "Enter short description (kebab-case): " DESCRIPTION
if [ -z "$DESCRIPTION" ]; then
    echo "Description required"
    exit 1
fi

# Validate kebab-case
if [[ ! "$DESCRIPTION" =~ ^[a-z0-9-]+$ ]]; then
    echo "Description must be lowercase letters, numbers, and hyphens only"
    exit 1
fi

# Build branch name
BRANCH_NAME="${PREFIX}/${DESCRIPTION}"

# Check if branch exists
if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
    echo "Branch '$BRANCH_NAME' already exists"
    read -p "Switch to it? (y/n): " SWITCH
    if [ "$SWITCH" = "y" ]; then
        git checkout "$BRANCH_NAME"
    fi
    exit 0
fi

# Create and switch to branch
echo ""
echo "Creating branch: $BRANCH_NAME"
git checkout -b "$BRANCH_NAME"
echo "Branch created and switched!"