---
name: Code Review
description: This skill should be used when the user asks to "review code", "check my code", "analyze this code", "code review", or wants feedback on code quality, security, or best practices.
version: 1.0.0
---

# Code Review Skill

When reviewing code, follow this systematic approach:

## 1. Initial Assessment

- Identify the purpose and scope of the code
- Check if the code accomplishes its stated goal
- Note any immediate red flags or concerns

## 2. Code Quality Checks

### Readability
- Clear and descriptive variable/function names
- Consistent formatting and indentation
- Appropriate comments for complex logic
- Functions are focused and single-purpose

### Structure
- Proper separation of concerns
- No deeply nested conditionals (max 3 levels)
- DRY principle followed (Don't Repeat Yourself)
- Appropriate use of design patterns

## 3. Security Review

- Input validation on all user inputs
- No hardcoded credentials or secrets
- Proper authentication and authorization checks
- SQL injection, XSS, and CSRF protection
- Secure handling of sensitive data

## 4. Performance Considerations

- Efficient algorithms and data structures
- No obvious N+1 queries
- Appropriate caching where beneficial
- Memory leak prevention

## 5. Error Handling

- Graceful error handling throughout
- Meaningful error messages
- Proper logging without sensitive data
- Edge cases considered

## 6. Testing

- Unit tests for core functionality
- Edge cases covered
- Test names describe what is being tested
- Mocked dependencies where appropriate

## Output Format

Provide feedback in this structure:

```
## Summary
Brief overall assessment

## Strengths
- What's done well

## Issues Found
### Critical
- Must fix before merge

### Important
- Should be addressed

### Suggestions
- Nice to have improvements

## Security Notes
- Any security concerns

## Recommendations
- Actionable next steps
```