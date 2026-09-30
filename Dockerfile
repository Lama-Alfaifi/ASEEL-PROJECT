
# Frontend build

FROM node:20-slim AS frontend-build

WORKDIR /frontend

COPY aseel-frontend/package*.json ./

RUN npm ci

COPY aseel-frontend/ ./

RUN npm run build



# Backend + frontend

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Replace the source frontend dist with the Docker-built dist
COPY --from=frontend-build /frontend/dist ./aseel-frontend/dist

EXPOSE 8000

CMD ["python", "aseel-frontend/serve_ui.py"]