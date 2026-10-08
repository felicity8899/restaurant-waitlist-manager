# Agent Collaboration Manual (AGENTS.md)

Welcome, AI Agent! This document contains critical context, guidelines, and commands to help you navigate, extend, and maintain the **Restaurant Waitlist & Table Manager** codebase efficiently and safely.

---

## 1. Project Context & Philosophy
This is a real-time web application containing a mobile-friendly guest waitlist portal and an interactive host management dashboard. 

### Core Decoupling Philosophy
All backend API and network logic is encapsulated within a centralized **Unified Service Layer**. Do not write inline `fetch`, Axios, or WebSocket calls inside React components. Instead, always use the `useApi()` hook to interact with the system.

---

## 2. Directory Structure & Key Entities
```
/
├── DESIGN.md                 # System requirements and database schemas
├── AGENTS.md                 # This instruction file for AI agents
├── _docs/
│   └── tasks.md              # Granular developer backlog/issues
└── frontend/
    ├── src/
    │   ├── types/
    │   │   └── index.ts      # Shared domain TypeScript types
    │   ├── services/
    │   │   ├── ApiService.ts     # Unified service interface
    │   │   ├── MockApiService.ts # Standalone browser-side mock backend
    │   │   └── FastApiService.ts # Production REST/WS backend client
    │   ├── contexts/
    │   │   └── ApiContext.tsx    # React Context and useApi() hook
    │   └── test/
    │       └── setup.ts          # Vitest and JSDOM global matches setup
    ├── package.json
    ├── tsconfig.json
    └── vite.config.ts
```

---

## 3. The Centralized API Service Layer
When adding features, modifications are typically made across three service files:

1. **`ApiService.ts`**: The TypeScript interface. Any new backend call must be defined here first.
2. **`MockApiService.ts`**: The in-memory local mock. You **must** implement any new interface methods here. This ensures that the frontend can be fully demonstrated and tested in standalone mode without a real Python server.
3. **`FastApiService.ts`**: The production fetch client. Implement the corresponding HTTP/REST or WebSocket endpoint call here.

### Dependency Injection
The service is injected using standard React Context.
- Default mode: The app runs with the `MockApiService` enabled (`import.meta.env.VITE_USE_MOCK_API` is empty or true).
- Production/Connected mode: The app switches to `FastApiService` when `import.meta.env.VITE_USE_MOCK_API === 'false'`.

---

## 4. Agent Development Guidelines

### Keep Mock Backend & Real Backend Aligned
Whenever you add a new endpoint or backend mutation:
- Implement corresponding mock state logic inside `MockApiService.ts`.
- Match the exact status codes, body response shapes, and throwing behavior.
- Ensure state events are broadcast via the subscription pattern (`this.broadcast('EVENT_NAME')`) to trigger hot-reloads on other mock pages.

### Testing Rules
Every code modification must be accompanied by relevant test updates:
- Write unit tests for service state changes in `src/services/__tests__/MockApiService.test.ts`.
- Write component rendering and context provider tests in `src/contexts/__tests__/ApiContext.test.tsx`.
- **Always verify changes** before final delivery by running the complete test suite and TypeScript check.

---

## 5. Standard Verification Commands

Run these commands inside the `frontend/` directory to ensure system stability:

### 1. Install Dependencies
```bash
npm install
```

### 2. Run Test Suite (Vitest)
```bash
npm test
```

### 3. Run TypeScript Compiler (Strict Type Check)
```bash
npx tsc --noEmit
```
