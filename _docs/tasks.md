# Project Backlog - Restaurant Waitlist & Table Manager

This backlog contains the development tasks required to build the Restaurant Waitlist & Table Manager web application. Each task is self-contained, independent, and designed to fit in a single session.

---

## 1. Project Initialization & Passing Test
Goal: Scaffold the React frontend and FastAPI backend directories and verify the environment with a passing test in each.
Description: Create the repository structure containing a `backend/` directory with a minimal FastAPI app and a `frontend/` directory with a standard React TypeScript project. Configure simple test environments for both (pytest for Python and Vitest/Jest for React) and write a single, basic assertion test in each that runs and passes successfully.

## 2. Database Models and SQLite Schema
Goal: Define the SQLite database schema and SQLAlchemy ORM models for tables, waitlist, and SMS logs.
Description: Implement the SQLAlchemy models for `tables`, `waitlist`, and `sms_logs` with the correct column types, primary/foreign keys, and constraints. Create an initialization script that creates the SQLite database file and tables automatically, and write unit tests to verify database creation and basic CRUD operations.

## 3. Backend Table REST API
Goal: Implement FastAPI endpoints to manage physical table states.
Description: Build backend REST endpoints to retrieve all tables and clear a specific table, transitioning it back to available or dirty. Write unit tests to verify that these API routes successfully interact with the database and return correct JSON payloads.

## 4. Backend Waitlist REST API
Goal: Implement FastAPI endpoints to add guests and view the queue.
Description: Build backend REST endpoints for guests to join the waitlist (`POST /api/waitlist`) and for hosts to retrieve the active queue. Write comprehensive unit tests validating guest data insertion, payload structures, and queue ordering.

## 5. Backend Seating and Notification API
Goal: Implement backend business logic for notifying and seating waitlist guests.
Description: Create API endpoints to transition guest status to `NOTIFIED` (triggering a log entry in `sms_logs`) and to `SEATED` (assigning the guest to an eligible table and updating the table's state). Write unit tests to verify that status transitions are correct, table capacities are respected, and mock SMS alerts are generated.

## 6. Real-Time WebSocket Hub
Goal: Build a WebSocket server in FastAPI to broadcast waitlist and table state changes to clients.
Description: Implement a WebSocket connection manager that tracks active dashboard and tracker clients. Create a broadcasting utility to send live status update events whenever waitlist entries or tables change state, and include tests simulating active clients receiving state updates.

## 7. Staff Access Control and Routing
Goal: Build frontend router security and a simulated PIN modal on the React application.
Description: Implement a secure login modal in React requiring the PIN `1234` to authorize access to the Host Dashboard views. Store the authorization status in session storage and guard host routes so that unauthenticated requests are redirected back to guest views.

## 8. Host Dashboard Waitlist Queue UI
Goal: Design and build the host dashboard queue view in the React application.
Description: Create a clean list or table interface on the Host Dashboard showing all currently waiting and notified parties. Include interactive action buttons on each party card to either notify or seat the party, integrating them with the corresponding backend REST APIs.

## 9. Host Dashboard Table Map UI
Goal: Build an interactive visual table layout for hosts to track seating availability.
Description: Construct a grid of table cards on the Host Dashboard color-coded by occupancy and cleanliness status (Available, Occupied, Dirty). Display seated party details directly on occupied table cards and include a button to trigger the table-clearing API on dirty or occupied tables.

## 10. Self-Service Guest Join Page
Goal: Build a mobile-optimized frontend form for guests to register themselves onto the waitlist.
Description: Design a clean page at `/guest/join` containing an intuitive registration form for guest name, party size, and phone number. On successful submission, call the backend waitlist API and automatically redirect the guest to their live tracker page.

## 11. Real-Time Guest Tracker Page
Goal: Build a live-updating tracker page for guests to monitor their waitlist status.
Description: Create a mobile-first page at `/guest/track/{party_id}` that displays the guest's current state and position in the queue. Establish a WebSocket connection to receive live backend state broadcasts, automatically displaying an alert banner when the host notifies them.

## 12. Mock SMS Visualizer Widget
Goal: Build a visual console on the dashboard to inspect outgoing simulated SMS notifications.
Description: Construct a side panel or modal widget that queries and displays the recent contents of the `sms_logs` table. Ensure that whenever any mock SMS notifications are sent, they instantly appear in this log pane with a timestamp and recipient phone number for easy interactive testing.
