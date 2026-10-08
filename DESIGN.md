# Restaurant Waitlist & Table Manager - Technical Design Document

## 1. Project Overview
A real-time **Restaurant Waitlist & Table Manager** web application that provides:
- **For Guests:** A mobile-friendly interface to join the waitlist, track their live position in queue, and receive real-time notifications when their table is ready.
- **For Staff/Hosts:** A dashboard to manage the waitlist queue, define physical tables, visual-track table availability, assign waiting parties to tables, and send notifications.

---

## 2. Technical Stack
- **Frontend:** React 18, TypeScript, Tailwind CSS, Lucide Icons
- **Backend:** Python 3.10+, FastAPI (Asynchronous framework), WebSockets for real-time status synchronization
- **Database:** SQLite (SQLAlchemy ORM) for lightweight, single-file local storage
- **SMS System:** Localized Mock SMS Center (simulates text message delivery via a shared database logs/UI interface for interactive testing)

---

## 3. Data Models & Database Schema

### Table: `tables`
Represents physical seating tables within the restaurant.
- `id` (Integer, Primary Key)
- `name` (String, e.g., "Table 1", "Booth 4")
- `capacity` (Integer, maximum guests)
- `status` (Enum: `AVAILABLE`, `OCCUPIED`, `DIRTY`)
- `current_party_id` (Integer, Foreign Key to `waitlist.id`, Nullable)

### Table: `waitlist`
Represents customer parties waiting to be seated or currently seated.
- `id` (Integer, Primary Key)
- `guest_name` (String)
- `party_size` (Integer)
- `phone_number` (String)
- `status` (Enum: `WAITING`, `NOTIFIED`, `SEATED`, `CANCELLED`)
- `joined_at` (DateTime, auto-now-add)
- `notified_at` (DateTime, Nullable)
- `seated_at` (DateTime, Nullable)
- `table_id` (Integer, Foreign Key to `tables.id`, Nullable)

### Table: `sms_logs`
Logs mock SMS text alerts sent to guests for simulated demonstration.
- `id` (Integer, Primary Key)
- `phone_number` (String)
- `message` (String)
- `sent_at` (DateTime, auto-now-add)

---

## 4. Architectural Components & Interactions

```
+-------------------------------------------------------------+
|                       Host Dashboard                        |
|   - Real-time Waitlist Queue                                |
|   - Interactive Table Map (Seat/Clear tables)               |
|   - Mock SMS Inbox / Outbox                                 |
+------------------------------+------------------------------+
                               | WebSockets / REST API
                               v
+-------------------------------------------------------------+
|                     FastAPI Backend                         |
|   - REST API (CRUD operations for waitlist and tables)       |
|   - WebSocket Hub (Broadcasts status changes)               |
|   - SQLite Database & SQLAlchemy ORM                        |
+------------------------------^------------------------------+
                               | WebSockets / REST API
+------------------------------+------------------------------+
|                         Guest Portal                        |
|   - QR Code Entry Point                                     |
|   - "Join Waitlist" Form                                    |
|   - Live Waitlist Status (Updates in real-time)             |
+-------------------------------------------------------------+
```

---

## 5. Main Workflows

### A. Guest Joins Waitlist
1. Guest scans QR code, opening `http://<host>/guest/join`.
2. Guest enters name, party size, and phone number, then clicks **Join Waitlist**.
3. Frontend sends `POST /api/waitlist` request.
4. Backend adds guest to the `waitlist` table in state `WAITING`.
5. Backend broadcasts updated waitlist queue to all host and guest WebSocket connections.
6. Guest is redirected to the Live Tracker page (`/guest/track/<party_id>`).

### B. Host Notifies Guest
1. Host views the Waitlist Queue on the Host Dashboard and clicks **Notify** on a party.
2. Frontend sends `POST /api/waitlist/<party_id>/notify` request.
3. Backend updates party status to `NOTIFIED` and records `notified_at`.
4. Backend appends a mock text alert to `sms_logs`.
5. Backend broadcasts the status change.
6. Guest's active browser tracker updates in real-time with an alert: *"Your table is ready! Please proceed to the host stand."*

### C. Host Seats Guest
1. Host clicks **Seat** on a party (either from `WAITING` or `NOTIFIED` status).
2. Host is shown eligible tables (status is `AVAILABLE` and table capacity matches/exceeds party size).
3. Host selects a table and clicks **Confirm**.
4. Frontend sends `POST /api/waitlist/<party_id>/seat` with `table_id`.
5. Backend updates:
   - `waitlist` entry status to `SEATED`, sets `table_id` and `seated_at`.
   - `tables` entry status to `OCCUPIED` and sets `current_party_id = party_id`.
6. Backend broadcasts table layout and queue updates.

### D. Host Clears Table
1. Guest finishes meal; host clicks **Clear Table** on the table map.
2. Frontend sends `POST /api/tables/<table_id>/clear` request.
3. Backend updates:
   - `tables` entry status to `DIRTY` (or `AVAILABLE` based on clean settings).
   - If setting to `DIRTY`, host can later toggle to `AVAILABLE` once wiped clean.
4. Backend broadcasts state updates.

---

## 6. Access Control (Simulated Staff Security)
To toggle between the **Guest Portal** and **Host Dashboard**, the UI will include a secure-looking PIN access modal:
- Staff PIN: `1234`
- Correct input unlocks session storage authorization, permitting access to `/admin` dashboard views and APIs.

---

## 7. Next Steps & Development Milestones
1. **Repository Scaffolding:** Create `backend/` and `frontend/` directories.
2. **Backend Setup:** Write SQLAlchemy database code, API endpoints, and WebSocket connections using FastAPI.
3. **Frontend Implementation:** Set up React with Tailwind, implement state synchronization, and construct the beautiful dashboard views.
4. **Integration Testing:** Run end-to-end user simulation of guests joining, getting notified, and being seated.
