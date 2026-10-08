# Restaurant Waitlist & Table Manager

A real-time, database-backed restaurant queue and table management system. It features a modern, clean React dashboard frontend that communicates dynamically with a FastAPI backend server using REST APIs and WebSockets.

---

## ✨ Key Features

### 🔐 Administrative & Staff Controls
- **Host & Staff PIN Authentication**: Administrative screens are secured using a simulated 4-digit PIN access portal (`1234`), saving an authentication session in local storage.
- **Dynamic Waitlist Queue Management**: Interactive queue dashboard allowing staff to track wait times, send table-ready alerts, seat parties, or cancel reservations.
- **Interactive Floor Layout Map**: Color-coded visual tables map reflecting real-time occupancy status:
  - 🟢 **AVAILABLE**: Ready for seating.
  - 🔴 **OCCUPIED**: Seating a party automatically updates the table state and links it to the guest.
  - 🟡 **DIRTY**: Clearing a seated table marks it as dirty for sanitation; clearing a second time restores it to available.

### 📱 Customer-Facing Guest Utilities
- **Self-Service Waitlist Registration**: Clean, responsive mobile-friendly form at `/guest/join` allows customers to easily register their name, party size, and phone number to the waitlist queue.
- **Live Real-Time Guest Tracker**: Personalized tracker screen at `/guest/track/{party_id}` dynamically updates to show current queue position, waiting status, and instant animated banners when notified by staff.

### ⚡ Real-Time Synchronization & SMS Simulation
- **Instantaneous WebSockets Update Broadcasts**: Active state changes (waitlist entries, table configurations, notifications) are instantly propagated using FastAPI WebSockets.
- **Integrated SMS Simulator Widget**: Outgoing simulated SMS alerts are dynamically captured in a dedicated console feed, enabling seamless real-time visual testing of client notifications.

---

## 🏗️ Architecture

- **Frontend**: React (TypeScript, Vite) with Lucide Icons. Default configured to connect to the real backend.
- **Backend**: FastAPI (Python 3.9+) with a unified data-access repository.
- **Database**: SQLite (local file database by default), powered by SQLAlchemy ORM for database-agnostic operations (ready for PostgreSQL/MySQL/etc.).

---

## 📋 Prerequisites

Ensure you have the following installed on your machine:
- **Python**: version 3.9 or higher
- **Node.js**: version 18.0 or higher
- **npm**: version 9.0 or higher

---

## ⚡ Quick Start

### Method A: Using `make` (Easiest)

If you have the `make` tool installed, simply run the following commands from the root directory:

1. **Install all dependencies** (Backend pip + Frontend npm):
   ```bash
   make install
   ```

2. **Start both Frontend and Backend concurrently**:
   ```bash
   make start
   ```
   - *Backend runs on*: `http://localhost:8000`
   - *Frontend runs on*: `http://localhost:5173`
   - *API Interactive Docs*: `http://localhost:8000/docs`

---

### Method B: Manual Startup (Step-by-Step)

If `make` is not available on your system, execute the following commands in separate terminal sessions:

#### 1. Start the Backend
```bash
# Navigate to backend directory
cd backend

# Install python dependencies
pip install -r requirements.txt

# Start the FastAPI server using uvicorn
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 2. Start the Frontend
```bash
# Navigate to frontend directory
cd frontend

# Install node packages
npm install

# Start the React development server
npm run dev -- --host 0.0.0.0
```

---

## 🗄️ Database Configuration (`DATABASE_URL`)

The application is built to be **database-agnostic** using SQLAlchemy ORM. By default, it creates a local SQLite database named `restaurant.db` in the `backend/` directory.

To configure a custom database, set the `DATABASE_URL` environment variable before starting the backend server:

```bash
# Example 1: Use a specific custom SQLite file path
export DATABASE_URL="sqlite:///my_custom_store.db"

# Example 2: Use an ephemeral, in-memory SQLite database (great for isolated sessions)
export DATABASE_URL="sqlite://"

# Example 3: Connect to an external PostgreSQL database (later integration)
export DATABASE_URL="postgresql://username:password@localhost:5432/my_restaurant_db"

# Start the server with the configured environment variable
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

*Note: For testing or in-memory SQLite configurations (`sqlite://`), the backend automatically configures a thread-safe connection pooling system (`StaticPool`) to guarantee state is correctly shared across asynchronous HTTP requests.*

---

## 🧪 Running the Test Suite

The project includes thorough, automated unit and integration tests for both frontend and backend architectures.

### Backend Tests (pytest)
Backend tests include API endpoints verification and dynamic database connection testing.
```bash
cd backend

# Option A: Run using local database
PYTHONPATH=. pytest

# Option B: Run on a completely isolated in-memory database (Highly Recommended!)
DATABASE_URL=sqlite:// PYTHONPATH=. pytest
```

### Frontend Tests (Vitest)
Frontend tests cover API connectivity states, Providers, and mock contexts.
```bash
cd frontend

# Run all tests once
npm test

# Run tests in watch mode
npm run test:watch
```

---

## 🛠️ Production Frontend Build

To build a production-ready, highly optimized, type-checked bundle of the React frontend application:

```bash
cd frontend
npm run build
```
The compiled, production assets will be generated inside the `frontend/dist/` directory, ready to be served by Nginx, Caddy, or static hosting providers.
