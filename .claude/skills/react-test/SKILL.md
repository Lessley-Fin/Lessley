---
name: react-test
description: 'Run Vitest tests for the Lessley React frontend. Use when: verifying component behavior, testing hooks, checking auth store logic, validating route guards, or running the test suite before committing.'
argument-hint: 'react-test to run the frontend test suite'
user-invocable: true
---

# React Tests

Run the Vitest test suite for the Lessley frontend.

## Commands

```bash
# Watch mode (re-runs on file changes)
cd lessley-frontend && npm run test

# Single run (CI mode)
cd lessley-frontend && npm run test:run
```

## Test Infrastructure

- **Runner:** Vitest 4.x (Vite-native, no separate config)
- **Environment:** jsdom (browser DOM simulation)
- **Assertions:** `@testing-library/jest-dom` (DOM matchers like `toBeInTheDocument`)
- **Rendering:** `@testing-library/react` + custom `renderWithProviders` wrapper
- **User interaction:** `@testing-library/user-event`

## Writing Tests

### Test file location

Place test files next to the code they test:
```
features/auth/store.ts       → features/auth/store.test.ts
routes/ProtectedRoute.tsx    → routes/ProtectedRoute.test.tsx
lib/query-keys.ts            → lib/query-keys.test.ts
```

### Custom render helper

Use `renderWithProviders` from `src/test/test-utils.tsx` to wrap components with all necessary providers (QueryClient, Router):

```tsx
import { renderWithProviders } from "@/test/test-utils"

it("renders the component", () => {
  renderWithProviders(<MyComponent />)
  expect(screen.getByText("Hello")).toBeInTheDocument()
})
```

### Testing Zustand stores

Access and reset store state directly in tests:

```ts
import { useAuthStore } from "@/features/auth/store"

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState({ isAuthenticated: false, accessToken: null, ... })
})
```

### Testing TanStack Query hooks

Wrap in a QueryClientProvider with `retry: false` for predictable test behavior. The `renderWithProviders` helper does this automatically.

## Current Test Coverage

- Auth store: login, logout, initialize, setProfile, setAccessToken
- ProtectedRoute: redirect when unauthenticated, render when authenticated
- Query keys: stable key generation with parameters
