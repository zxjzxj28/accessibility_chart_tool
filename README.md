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
2. Configure environment variables as needed (or edit the defaults in
   `backend/config.py` if you prefer to hard-code local settings):
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

### Schema overview

The application persists three core entities. Column types reflect their SQLAlchemy definitions and are compatible with MySQL and SQLite alike.

| Table | Columns |
| --- | --- |
| `users` | `id` (PK, INT, auto increment), `email` (VARCHAR(120), unique, not null), `name` (VARCHAR(120), not null), `password_hash` (VARCHAR(255), not null), `created_at` (DATETIME, default current timestamp) |
| `chart_groups` | `id` (PK, INT, auto increment), `name` (VARCHAR(120), not null), `user_id` (FK → `users.id`, not null), `created_at` (DATETIME, default current timestamp) |
| `chart_tasks` | `id` (PK, INT, auto increment), `title` (VARCHAR(255), not null), `status` (VARCHAR(50), default `'pending'`), `user_id` (FK → `users.id`, not null), `group_id` (FK → `chart_groups.id`, nullable), `image_path` (VARCHAR(500)), `summary` (TEXT), `description` (TEXT), `data_points` (JSON), `table_data` (JSON), `generated_code` (LONGTEXT/TEXT), `custom_code` (LONGTEXT/TEXT), `error_message` (TEXT), `created_at` (DATETIME, default current timestamp), `updated_at` (DATETIME, default current timestamp, auto-update on change) |

### SQL definition

For environments that require manual bootstrap, run the following SQL script (MySQL syntax) to create all tables. Adjust data types if your target database lacks JSON support.

```sql
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(120) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chart_groups (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  user_id INT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_chart_groups_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chart_tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  user_id INT NOT NULL,
  group_id INT NULL,
  image_path VARCHAR(500) NULL,
  summary TEXT NULL,
  description TEXT NULL,
  data_points JSON NULL,
  table_data JSON NULL,
  generated_code LONGTEXT NULL,
  custom_code LONGTEXT NULL,
  error_message TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_chart_tasks_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_chart_tasks_group
    FOREIGN KEY (group_id) REFERENCES chart_groups(id)
    ON DELETE SET NULL
);
```

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
