# =========================================================
# Stage 1: Build the React TypeScript frontend using Node
# =========================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend configuration and dependency manifests
COPY frontend/package*.json ./

# Install dependencies using clean install (ci)
RUN npm ci

# Copy the rest of the frontend source files
COPY frontend/ ./

# Build the production optimized static files
RUN npm run build

# =========================================================
# Stage 2: Create Python image with FastAPI & static assets
# =========================================================
FROM python:3.9-slim AS backend-server

WORKDIR /app

# Expose port 8000 for the FastAPI server
EXPOSE 8000

# Set Python environment flags and database defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:///restaurant.db

# Copy requirements and install backend dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code and pre-populated database
COPY backend/app/ ./app/
COPY backend/restaurant.db ./restaurant.db

# Copy compiled static frontend assets from Stage 1 into backend's static directory
COPY --from=frontend-builder /app/frontend/dist/ ./static/

# Run the FastAPI server using uvicorn on all network interfaces
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
