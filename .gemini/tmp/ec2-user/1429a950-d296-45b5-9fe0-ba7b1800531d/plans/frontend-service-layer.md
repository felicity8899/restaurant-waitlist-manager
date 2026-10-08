# System Design Plan: Centralized Frontend Service Layer

## 1. Objective
Design and implement a centralized API service layer in the React frontend that abstracts all backend interactions. This will allow the application to run fully functionally using an in-memory mock implementation without a real backend, while easily swapping to the real FastAPI backend when available. Ensure both implementations and components are comprehensively tested.

## 2. Background & Motivation
Currently, the backlog anticipates standard REST calls embedded in frontend components. By centralizing all data fetching and real-time WebSocket interactions into a single interface, we decouple the UI from the network layer. This provides two massive benefits:
1. **Rapid Prototyping & Demos:** The app can be run 100% locally in the browser using the mock backend, enabling design and testing without spinning up the database or Python server.
2. **Robust Testing:** UI components can be tested deterministically by supplying the mock service, avoiding flaky network tests.

## 3. Scope & Impact
This design will dictate how all React components retrieve and mutate data. It introduces:
- A core TypeScript `ApiService` interface.
- Two concrete classes: `MockApiService` and `FastApiService`.
- A React Context (`ApiProvider`) to supply the instantiated service down the component tree.
- Comprehensive unit testing for the mock logic and component rendering.

## 4. Proposed Solution

### A. The Core Interface (`src/services/ApiService.ts`)
We will define an interface that exposes asynchronous methods for all application requirements:
- `getWaitlist()`, `joinWaitlist(guest)`, `updateStatus(partyId, status)`
- `getTables()`, `clearTable(tableId)`, `seatParty(partyId, tableId)`
- `getSmsLogs()`
- Real-time subscription: `subscribe(callback)` to listen for overarching state changes.

### B. Mock Implementation (`src/services/MockApiService.ts`)
An implementation that stores waitlist, tables, and SMS logs in private class arrays. It will simulate network latency (e.g., 200ms delays via `setTimeout`) and simulate backend event broadcasts whenever a state mutation occurs. 

### C. Real Implementation (`src/services/FastApiService.ts`)
An implementation that executes standard `fetch` API calls to the FastAPI endpoints and maintains a persistent `WebSocket` connection to receive live broadcasts.

### D. Dependency Injection (`src/contexts/ApiContext.tsx`)
A React context will provide the service instance. The root of the application will read an environment variable (e.g., `VITE_USE_MOCK_API=true`) and instantiate the appropriate class, passing it into the `<ApiProvider>`. Components will use a `useApi()` hook to access it.

## 5. Implementation Steps
1. **Define Types & Interfaces:** Create the shared data types (`Guest`, `Table`, `WaitlistEntry`) and the `ApiService` interface.
2. **Build Mock Backend:** Implement `MockApiService` with realistic in-memory data, state mutations, and an event emitter.
3. **Build Real Backend Stub:** Implement `FastApiService` (even if the actual backend isn't built yet, the fetch signatures will be ready).
4. **Setup React Context:** Create `ApiContext.tsx`, `ApiProvider`, and the `useApi` hook.
5. **Update App Root:** Wrap the application in `<ApiProvider>` with environment variable toggling.

## 6. Verification & Testing Strategy
- **Service Unit Tests:** Write Vitest tests against `MockApiService` to ensure it enforces business logic (e.g., cannot seat a party at an occupied table).
- **Component Tests:** Write React Testing Library tests for key components (e.g., the Host Dashboard), passing in the `MockApiService` to verify rendering and interactive state updates.
