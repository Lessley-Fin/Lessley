---
name: react-feature
description: 'Guide for creating new features in the Lessley React frontend. Use when: adding a new page, feature module, or API integration following the established architecture patterns.'
argument-hint: 'react-feature for guidance on adding new features'
user-invocable: true
---

# React Feature Module Guide

Follow this pattern when adding a new feature to the Lessley frontend.

## Feature Module Structure

Each feature lives under `src/features/<name>/` with this structure:

```
features/<name>/
├── <Name>Page.tsx       — Page component (route target)
├── api.ts               — Raw API fetch functions (use apiFetch)
├── hooks.ts             — TanStack Query hooks (useQuery, useMutation)
└── types.ts             — Feature-specific TypeScript interfaces (optional)
```

## Step-by-Step

### 1. Create the API layer

```typescript
// features/example/api.ts
import { apiFetch } from "@/lib/api-client"

export interface ExampleItem {
  id: string
  name: string
}

export async function fetchExamples(): Promise<ExampleItem[]> {
  return apiFetch<ExampleItem[]>("/api/Example")
}

export async function createExample(data: { name: string }): Promise<void> {
  await apiFetch("/api/Example", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
}
```

### 2. Add query keys

```typescript
// lib/query-keys.ts — add to the existing factory
export const queryKeys = {
  // ... existing keys
  examples: {
    all: ["examples"] as const,
    list: () => [...queryKeys.examples.all, "list"] as const,
  },
}
```

### 3. Create TanStack Query hooks

```typescript
// features/example/hooks.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { queryKeys } from "@/lib/query-keys"
import { fetchExamples, createExample } from "./api"

export function useExamples() {
  return useQuery({
    queryKey: queryKeys.examples.list(),
    queryFn: fetchExamples,
  })
}

export function useCreateExample() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createExample,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.examples.all })
    },
  })
}
```

### 4. Create the page component

```typescript
// features/example/ExamplePage.tsx
import { useExamples } from "./hooks"

export function ExamplePage() {
  const { data: items = [], isLoading } = useExamples()

  if (isLoading) return <p>Loading...</p>

  return (
    <section className="fintech-page">
      {items.map(item => <div key={item.id}>{item.name}</div>)}
    </section>
  )
}
```

### 5. Add the route

```typescript
// routes/index.tsx — add to the route tree
const ExamplePage = lazy(() =>
  import("@/features/example/ExamplePage").then(m => ({ default: m.ExamplePage }))
)

// Inside the ProtectedRoute > AppLayout children:
{
  path: "example",
  element: (
    <Suspense fallback={<SuspenseFallback />}>
      <ExamplePage />
    </Suspense>
  ),
}
```

## Key Rules

1. **`api.ts` files never import React** — they are pure async functions
2. **`hooks.ts` files wrap api functions with TanStack Query** — they are the React integration layer
3. **Page components use hooks, never api functions directly**
4. **No feature imports another feature's `api.ts`** — share via query cache or lib/
5. **Auth is automatic** — `apiFetch` handles token injection and refresh
6. **Use `fintech-*` CSS classes** from `lib/fintech-styles.ts` for consistent styling

## Styling Reference

```typescript
import { fintech } from "@/lib/fintech-styles"

// Available classes:
fintech.page          // Page container with spacing
fintech.card          // Card with shadow and rounded corners
fintech.cardInset     // Inset section within a card
fintech.listRow       // Row in a data list
fintech.sectionTitle  // Section heading
fintech.sectionEyebrow // Small uppercase label
fintech.metricBlue    // Blue metric card
fintech.metricViolet  // Violet metric card
fintech.amount        // Formatted amount text
fintech.input         // Styled input field
```
