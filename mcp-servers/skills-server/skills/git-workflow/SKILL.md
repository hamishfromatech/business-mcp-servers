---
name: Git Workflow
description: This skill should be used when the user asks to "commit changes", "create a branch", "git workflow", "smart commit", or needs help with git operations and best practices.
version: 1.0.0
---

# Git Workflow Skill

Follow these best practices for git operations:

## Branch Naming Convention

- `feature/short-description` - New features
- `fix/issue-description` - Bug fixes
- `docs/what-changed` - Documentation updates
- `refactor/component-name` - Code refactoring
- `test/test-description` - Adding/updating tests

## Commit Message Format

```
type(scope): short description

[optional body]

[optional footer]
```

### Types
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting, no code change
- `refactor` - Code refactoring
- `test` - Adding tests
- `chore` - Maintenance tasks

## Before Committing

1. Run tests if available
2. Check for linting errors
3. Review diff with `git diff`
4. Stage only related changes
5. Write meaningful commit message

## Workflow Steps

1. Pull latest changes from main
2. Create feature branch
3. Make changes with atomic commits
4. Push branch and create PR
5. Address review feedback
6. Squash and merge

## Scripts

This skill includes helper scripts:
- `smart-commit.sh` - Interactive commit helper
- `create-branch.sh` - Branch creation with naming validation