# Technical Specification (spec.md)

This document defines the comprehensive technical specification, database models, REST API endpoints, WebSocket event flows, and strict business validation constraints for the **Restaurant Waitlist & Table Manager**.

---

## 1. System Overview
The system coordinates and syncs real-time state changes between guests waiting for a table and restaurant staff managing physical table configurations.

---

## 2. Data Models & Database Schema

The database is powered by an lightweight SQLite instance using SQLAlchemy in production, mirrored in memory by the unified service layer.

### A. Table Entity (`tables`)
Represents physical restaurant dining tables.
- `id` (Integer, Primary Key, Auto-Increment)
- `name` (String, Unique, e.g., "Table 1", "Booth 4")
- `capacity` (Integer, Minimum: 1, represents seating capacity)
- `status` (Enum: `AVAILABLE`, `OCCUPIED`, `DIRTY`)
- `current_party_id` (Integer, Foreign Key to `waitlist.id`, Nullable, defaulted to Null)

### B. Waitlist Entity (`waitlist`)
Represents customer parties who are either queued or currently seated.
- `id` (Integer, Primary Key, Auto-Increment)
- `guest_name` (String, Non-Empty)
- `party_size` (Integer, Minimum: 1)
- `phone_number` (String, formatted contact number)
- `status` (Enum: `WAITING`, `NOTIFIED`, `SEATED`, `CANCELLED`)
- `joined_at` (DateTime, ISO-8601 string representation)
- `notified_at` (DateTime, ISO-8601 string representation, Nullable)
- `seated_at` (DateTime, ISO-8601 string representation, Nullable)
- `table_id` (Integer, Foreign Key to `tables.id`, Nullable)

### C. SMS Log Entity (`sms_logs`)
Simulates outbound messaging logs for guests.
- `id` (Integer, Primary Key, Auto-Increment)
- `phone_number` (String)
- `message` (String)
- `sent_at` (DateTime, ISO-8601 string representation)

---

## 3. Strict Business Logic & Invariants

To maintain system integrity, both the frontend mock layer and backend service must strictly enforce the following rules:

### A. Guest Seating Constraints
1. **Status Check:** A party can only be seated if their current status is `WAITING` or `NOTIFIED`. Parties with status `SEATED` or `CANCELLED` are rejected.
2. **Table Availability:** A table can only be selected for seating if its current status is `AVAILABLE`. Tables marked as `OCCUPIED` or `DIRTY` are rejected.
3. **Capacity Check:** The physical capacity of the selected table must be greater than or equal to the guest's `party_size` (`table.capacity >= waitlist.party_size`).

### B. Notification Constraints
1. **Status Check:** A party can only be notified if their current status is `WAITING`.
2. **Notification Event:** Notifying a guest transitions their status to `NOTIFIED`, updates `notified_at` to the current time, and appends a mock log to the `sms_logs` table.

### C. Table Status Progression
1. When a table is initially cleared, its status transitions from `OCCUPIED` to `DIRTY`. The `current_party_id` is set to `Null`.
2. To restore table availability, staff must clear the table a second time, transitioning it from `DIRTY` to `AVAILABLE`.
3. If a guest's reservation is cancelled *while* they are seated, their associated table immediately transitions directly to `AVAILABLE` (cleaning step skipped for efficiency).

---

## 4. API Endpoint Contract

All REST APIs must exchange payloads formatted as JSON and return appropriate HTTP status codes (200/201 on success, 400/404 on logic/resource errors).

### A. Table APIs
- **`GET /api/tables`**: Returns a list of all tables and their statuses.
- **`POST /api/tables/{id}/clear`**: Cycles the table status (`OCCUPIED -> DIRTY` or `DIRTY -> AVAILABLE`).

### B. Waitlist APIs
- **`GET /api/waitlist`**: Returns the active waitlist queue (chronologically ordered by `joined_at`).
- **`POST /api/waitlist`**: Adds a new guest to the queue. Returns the entry.
  - Body: `{ guest_name: string, party_size: number, phone_number: string }`
- **`POST /api/waitlist/{id}/notify`**: Sends SMS notification and updates status to `NOTIFIED`.
- **`POST /api/waitlist/{id}/seat`**: Assigns guest to table and updates statuses.
  - Body: `{ table_id: number }`
- **`POST /api/waitlist/{id}/cancel`**: Cancels reservation and frees up associated table.

### C. SMS APIs
- **`GET /api/sms-logs`**: Retrieves all outbound simulated text messages.

### D. WebSocket Interface
- Endpoint: `/ws`
- Connection: Clients (Host/Guests) establish persistent connections to receive instantaneous push event messages.
- Events Broadcasted:
  - `QUEUE_UPDATE`: Triggered when guests join, update status, or cancel.
  - `TABLE_UPDATE`: Triggered when tables are cleared or occupied.
  - `SMS_UPDATE`: Triggered when guest notifications are sent.

---

## 5. Staff Access Verification (Simulated Security)
- Unlocked by a secure 4-digit PIN: `1234`.
- Valid entries generate a local browser token saved in `sessionStorage`.
- Attempting to access administrative endpoints or Host Dashboard screens without authorization prompts a redirect lock.
