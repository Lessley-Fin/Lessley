---
name: react-lint
description: 'Run ESLint on the Lessley React frontend. Use when: checking code quality, enforcing consistent patterns, or before committing frontend changes.'
argument-hint: 'react-lint to check code quality'
user-invocable: true
---

# React Lint

Run ESLint across all frontend source files.

## Command

```bash
cd lessley-frontend && npm run lint
```

## What it checks

- React Hooks rules (`eslint-plugin-react-hooks`)
- React Refresh compatibility (`eslint-plugin-react-refresh`)
- TypeScript best practices (`typescript-eslint`)

## Auto-fix

To auto-fix fixable issues:

```bash
cd lessley-frontend && npx eslint . --fix
```
