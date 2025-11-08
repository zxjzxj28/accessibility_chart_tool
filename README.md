# Accessibility Chart Tool

A full-stack developer tool that converts chart images into accessible front-end components for Android web views. The platform lets users upload chart images, processes them asynchronously, and produces accessible code snippets alongside data summaries. Each user can organise their generated charts in groups, edit the generated code, preview the results, and manage task history.

## Features

- User authentication with registration, login, logout, and password updates.
- Task management: create (upload), list, cancel, delete, and view detailed results.
- Asynchronous background worker that simulates cloud processing to extract summaries and data points.
- Automatic generation of accessible chart container code with focusable data points for screen reader support.
- Vue 3 front-end with task dashboard, chart grouping, code editor, and live preview sandbox.
- MySQL-compatible database layer via SQLAlchemy (defaults to SQLite for local development).

## Project structure

```
backend/
  app.py              # Flask application factory and bootstrap
  models.py           # SQLAlchemy models for users, groups, and tasks
  tasks.py            # Background worker handling chart processing
  utils/chart_processing.py  # Simulated cloud processing and code generation
  auth/               # Authentication blueprint
  charts/             # Task & group blueprint plus upload serving
frontend/
  src/                # Vue 3 single-page application
  package.json        # Front-end dependencies (Vite + Vue 3)
README.md             # This file
```

## Backend setup

1. Create a virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure environment variables as needed:
   - `DATABASE_URL`: SQLAlchemy connection string (e.g. `mysql+pymysql://user:pass@localhost/chart_tool`).
   - `SECRET_KEY`, `JWT_SECRET_KEY`: security secrets.
   - `UPLOAD_FOLDER`: optional custom path for image uploads.
3. Run the development server:
   ```bash
   flask --app app:create_app run
   ```
   The API will be available at `http://localhost:5000` and the background worker starts automatically.

## Frontend setup

1. Install dependencies and start the Vite dev server:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. The front-end proxies `/api` requests to `http://localhost:5000` via the Vite dev server configuration.

## Database notes

- By default, the backend uses SQLite for convenience. To switch to MySQL, set `DATABASE_URL` to a valid MySQL connection string before starting the server.
- Tables are created automatically on app start. For production usage, consider managing migrations separately.

## Simulated chart processing

The current implementation includes a simulated cloud processing pipeline (`backend/utils/chart_processing.py`). It opens the uploaded image, generates pseudo-random data points, and creates an accessible HTML code snippet. Replace the simulation with your actual cloud-based pipeline by updating the `process_chart` function.

## Testing the workflow

1. Register a new user via the front-end or API.
2. Create optional groups to organise chart conversions.
3. Upload a chart image to start a task. The dashboard refresh button retrieves the latest status.
4. Open a task detail page to inspect summaries, review the generated accessible component code, and customise the output. Use the embedded preview to validate changes.
5. Save custom code snippets or regenerate them from the stored data points.

---

This project provides a foundation for building a production-ready accessibility tooling suite. Extend it with real chart analysis pipelines, stricter validation, and additional user collaboration features as needed.
