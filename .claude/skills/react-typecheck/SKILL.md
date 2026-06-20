---
name: react-typecheck
description: 'Run TypeScript type checking on the Lessley React frontend without emitting output. Use when: checking for type errors, validating refactors, or debugging import issues.'
argument-hint: 'react-typecheck to check TypeScript types'
user-invocable: true
---

# React TypeScript Check

Run the TypeScript compiler in check-only mode (no output files).

## Command

```bash
cd lessley-frontend && npm run typecheck
```

## Configuration

- **Target:** ES2023
- **JSX:** react-jsx (automatic runtime)
- **Module:** ESNext with bundler resolution
- **Path aliases:** `@/*` → `./src/*`
- **Strict checks:** `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`
- **Erasable syntax only:** enabled (no `enum`, no constructor parameter properties)

## Common Issues

| Error | Fix |
|---|---|
| `TS1294: erasableSyntaxOnly` | Use `status: number` as a field, not `public status: number` in constructor |
| `Cannot find module '@/...'` | Check that the file exists under `src/` and the path alias is correct |
| Unused variable | Prefix with `_` or remove if genuinely unused |
