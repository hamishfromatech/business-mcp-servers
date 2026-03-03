#!/bin/bash
# Smart Commit Helper
# Guides user through creating a well-formatted commit message

echo "=== Smart Commit Helper ==="
echo ""

# Get staged files
STAGED=$(git diff --cached --name-only)
if [ -z "$STAGED" ]; then
    echo "No files staged. Stage files first with 'git add'"
    exit 1
fi

echo "Staged files:"
echo "$STAGED"
echo ""

# Prompt for commit type
echo "Select commit type:"
echo "  1) feat     - New feature"
echo "  2) fix      - Bug fix"
echo "  3) docs     - Documentation"
echo "  4) style    - Formatting"
echo "  5) refactor - Code refactoring"
echo "  6) test     - Adding tests"
echo "  7) chore    - Maintenance"
echo ""
read -p "Enter number (1-7): " type_num

case $type_num in
    1) TYPE="feat" ;;
    2) TYPE="fix" ;;
    3) TYPE="docs" ;;
    4) TYPE="style" ;;
    5) TYPE="refactor" ;;
    6) TYPE="test" ;;
    7) TYPE="chore" ;;
    *) echo "Invalid selection"; exit 1 ;;
esac

# Prompt for scope
read -p "Enter scope (optional, e.g., 'api', 'ui'): " SCOPE
if [ -n "$SCOPE" ]; then
    SCOPE="($SCOPE)"
fi

# Prompt for description
read -p "Enter short description: " DESCRIPTION
if [ -z "$DESCRIPTION" ]; then
    echo "Description required"
    exit 1
fi

# Build commit message
COMMIT_MSG="${TYPE}${SCOPE}: ${DESCRIPTION}"

# Confirm
echo ""
echo "Commit message:"
echo "  $COMMIT_MSG"
echo ""
read -p "Proceed? (y/n): " CONFIRM

if [ "$CONFIRM" = "y" ]; then
    git commit -m "$COMMIT_MSG"
    echo "Commit created!"
else
    echo "Cancelled"
fi