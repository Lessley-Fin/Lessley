---
name: react-build
description: 'Build the Lessley React frontend for production. Use when: preparing a deployment, checking that TypeScript compiles, or verifying the production bundle before shipping.'
argument-hint: 'react-build to compile and bundle the frontend'
user-invocable: true
---

# React Production Build

Build the Lessley frontend for production deployment.

## Command

```bash
cd lessley-frontend && npm run build
```

## What it does

1. Runs TypeScript type checking (`tsc -b`)
2. Bundles with Vite (Rolldown) into `dist/`
3. Code-splits lazy-loaded routes into separate chunks
4. Minifies and tree-shakes for smallest bundle size

## Output

Production files are written to `lessley-frontend/dist/`:
- `index.html` — entry point
- `assets/*.js` — JavaScript chunks (one per lazy route + shared)
- `assets/*.css` — compiled Tailwind CSS

## Troubleshooting

| Problem | Fix |
|---|---|
| TypeScript errors | Run `npm run typecheck` for detailed errors |
| Missing dependencies | Run `npm install` first |
| Build warnings about SignalR | Safe to ignore — upstream `/*#__PURE__*/` annotation placement |
