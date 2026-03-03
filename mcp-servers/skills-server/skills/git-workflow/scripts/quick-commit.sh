#!/bin/bash
# quick-commit.sh - Interactive commit message builder

echo "Git Quick Commit"
echo "================"
echo ""

# Select type
echo "Select commit type:"
echo "1) feat  - New feature"
echo "2) fix   - Bug fix"
echo "3) docs  - Documentation"
echo "4) style - Formatting"
echo "5) refactor - Code refactor"
echo "6) test  - Tests"
echo "7) chore - Maintenance"
echo ""
read -p "Enter number (1-7): " type_num

case $type_num in
    1) type="feat" ;;
    2) type="fix" ;;
    3) type="docs" ;;
    4) type="style" ;;
    5) type="refactor" ;;
    6) type="test" ;;
    7) type="chore" ;;
    *) echo "Invalid selection"; exit 1 ;;
esac

# Get scope
read -p "Enter scope (optional, e.g., 'auth', 'api'): " scope
if [ -n "$scope" ]; then
    scope="($scope)"
fi

# Get subject
read -p "Enter commit subject: " subject

# Build message
message="$type$scope: $subject"

echo ""
echo "Commit message:"
echo "  $message"
echo ""

read -p "Proceed with commit? (y/n): " confirm
if [ "$confirm" = "y" ]; then
    git commit -m "$message"
fi