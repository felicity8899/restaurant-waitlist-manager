.PHONY: help install start start-backend start-frontend test test-backend test-frontend test-integration e2e

help:
	@echo "Available commands:"
	@echo "  make install         - Install dependencies for both backend and frontend"
	@echo "  make start           - Start both backend and frontend concurrently"
	@echo "  make start-backend   - Start the FastAPI backend server"
	@echo "  make start-frontend  - Start the React frontend server (connected to backend)"
	@echo "  make test            - Run both backend and frontend tests"
	@echo "  make test-backend    - Run backend unit tests"
	@echo "  make test-frontend   - Run frontend unit tests"
	@echo "  make test-integration - Run end-to-end integration tests against docker-compose stack"
	@echo "  make e2e             - Run end-to-end integration tests against docker-compose stack"

install:
	@echo "Installing backend dependencies..."
	pip install -r backend/requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

start:
	@echo "Starting both backend and frontend concurrently..."
	make -j2 start-backend start-frontend

start-backend:
	@echo "Starting FastAPI backend on port 8000..."
	cd backend && PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000

start-frontend:
	@echo "Starting React frontend on port 5173..."
	cd frontend && VITE_USE_MOCK_API=false npm run dev -- --host 0.0.0.0

test: test-backend test-frontend

test-backend:
	@echo "Running backend tests on an isolated in-memory database..."
	cd backend && DATABASE_URL=sqlite:// PYTHONPATH=. pytest

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm test

test-integration:
	@echo "Running Docker Compose integration tests..."
	./scripts/integration_test.py

e2e:
	@echo "Running end-to-end integration tests..."
	./scripts/integration_test.py


