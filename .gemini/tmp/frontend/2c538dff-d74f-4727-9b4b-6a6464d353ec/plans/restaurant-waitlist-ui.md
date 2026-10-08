# Plan: Restaurant Waitlist UI Implementation

## Objective
Build out a functional, visually appealing, and real-time dashboard UI for the Restaurant Waitlist application. The layout will follow a "Dashboard (Side-by-side)" approach suitable for a host stand. The UI will integrate directly with the existing `ApiContext` and data services, avoiding external styling frameworks in favor of flexible, maintainable Vanilla CSS.

## Key Files & Context
- `index.html` (New): The application's HTML entry point.
- `src/main.tsx` (New): The React mounting script.
- `src/index.css` (New): Global styles, responsive dashboard layout, and interactive element styling.
- `src/App.tsx` (New): The root application component containing the primary side-by-side layout.
- `src/components/...` (New): Reusable components such as `Waitlist`, `TableGrid`, and `AddGuestForm`.
- `src/contexts/ApiContext.tsx` (Existing): Provides the `ApiService`.
- `src/services/` & `src/types/` (Existing): Defines the real-time API subscription and models.

## Implementation Steps

### 1. Setup Entry Points
- Create `index.html` at the project root with necessary meta tags and the mounting `div#root`.
- Create `src/main.tsx` to render the React application, importing `index.css`.

### 2. Design the Global Styles (Vanilla CSS)
- Create `src/index.css`.
- Define CSS variables for a consistent, modern color palette (e.g., slate grays, primary blues, and status colors like green for available, orange for occupied, red for dirty).
- Implement a CSS Grid layout for the `App` container to achieve the side-by-side dashboard look.
- Style forms, buttons, and cards with appropriate padding, border-radius, and hover states.

### 3. Build the Core Application Shell (`App.tsx`)
- Implement `App.tsx` wrapped in `<ApiProvider>`.
- Use a `useEffect` hook to subscribe to the real-time events (`TABLE_UPDATE`, `QUEUE_UPDATE`, `SMS_UPDATE`) emitted by the `ApiService`.
- Fetch the initial state (`getTables`, `getWaitlist`) when the component mounts.
- Render a header and the two main grid columns: one for the Waitlist/Adding Guests, and one for the Table Grid.

### 4. Implement Feature Components
- **AddGuestForm**: A simple form to input guest name, party size, and phone number, calling `joinWaitlist()`.
- **Waitlist**: A list rendering `WaitlistEntry` items. Include action buttons for "Notify" and "Cancel", and a dropdown/button interface to "Seat" the party at an available table.
- **TableGrid**: A visual representation of the restaurant floor showing `Table` items. Display capacity and current status. Include a "Clear Table" action for occupied/dirty tables.

## Verification & Testing
1. Ensure the application starts correctly using Vite (`npm run dev`).
2. Verify that adding a new guest instantly updates the waitlist UI.
3. Test notifying a party (verify the status changes to NOTIFIED).
4. Test seating a party at a table (verify the table becomes OCCUPIED and the party is marked SEATED).
5. Test clearing a table (verify it transitions from OCCUPIED -> DIRTY -> AVAILABLE).
6. Verify the dashboard layout holds up across standard desktop/tablet window sizes.