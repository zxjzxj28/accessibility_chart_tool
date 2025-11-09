# Accessibility Chart Tool — Implementation Overview

This document catalogues every major feature that currently exists in the Accessibility Chart Tool project and explains how each
piece is implemented. Use it as a reference when you need to understand the control flow across the Flask backend, the Vue front
end, and the background worker that transforms uploaded charts into accessible code snippets.

## System architecture at a glance

The product is a full-stack application composed of three layers:

1. **Flask backend (`backend/`)** — provides REST APIs for authentication, chart task management, image uploads, and custom code
   persistence. It also embeds a lightweight background worker that simulates the cloud-based chart analysis pipeline.
2. **Vue 3 front end (`frontend/`)** — a single-page application built with Vite and Pinia. It offers login/registration forms,
   a dashboard for managing groups and tasks, and a detail view with code editing plus live preview.
3. **Database and storage** — SQLAlchemy models back the relational schema (`users`, `chart_groups`, `chart_tasks`). Uploaded
   images are stored on disk inside the configured `UPLOAD_FOLDER`, namespaced per user, and are exposed via a Flask static route
   so that generated markup can reference them.

The following sections describe each feature in depth.

## Backend implementation details

### Application factory and configuration

- `backend/app.py` exposes `create_app`, the entry point used by the CLI or WSGI servers. It loads configuration from
  `backend/config.py`, creates the upload directory, enables CORS for `/api/*`, initialises the SQLAlchemy and JWT extensions,
  creates all tables, registers the authentication and chart blueprints, exposes a health-check route, and finally starts the
  background worker thread.【F:backend/app.py†L15-L41】
- Configuration classes (`Config`, `TestConfig`) define defaults for secrets, database URL, JWT expiry, upload directory, and
  request size limits. Each setting can be overridden by environment variables, but sensible development values are provided so
  the project runs without manual tweaks.【F:backend/config.py†L1-L34】

### Database models and relationships

- `backend/models.py` defines three SQLAlchemy models: `User`, `ChartGroup`, and `ChartTask`. Each includes helper methods to
  serialise records into JSON-friendly dictionaries consumed by the API responses.【F:backend/models.py†L1-L79】
  - `User` stores registration data and password hashes, exposes `set_password`/`check_password`, and has relationships to both
    groups and tasks.【F:backend/models.py†L10-L33】
  - `ChartGroup` captures user-owned collections that chart tasks can be assigned to.【F:backend/models.py†L36-L50】
  - `ChartTask` persists upload metadata, status, generated artefacts (summary, description, data points, table data, code, and
    custom overrides), and timestamps. Its `to_dict` method resolves the public URL for the uploaded image by calling the
    dedicated serving route.【F:backend/models.py†L53-L79】

### Authentication workflow

- The authentication blueprint (`backend/auth/routes.py`) implements registration, login, and password change endpoints.
  - `POST /api/auth/register` validates required fields, prevents duplicate emails, hashes the password, and stores the user.【F:backend/auth/routes.py†L11-L33】
  - `POST /api/auth/login` verifies credentials and returns a JWT access token along with basic user data for client-side state.【F:backend/auth/routes.py†L36-L51】
  - `POST /api/auth/change-password` requires a valid JWT, checks the current password, and updates the stored hash.【F:backend/auth/routes.py†L54-L71】
- Flask-JWT-Extended handles token creation/validation. The access token is short enough for SPA storage and is attached to
  subsequent requests by the front end via Axios defaults.

### Chart group management

- `GET /api/groups` fetches all groups that belong to the current user, sorted by creation date.【F:backend/charts/routes.py†L28-L35】
- `POST /api/groups` validates the payload, persists the new group, and returns its serialised representation.【F:backend/charts/routes.py†L38-L48】
- `DELETE /api/groups/<id>` ensures ownership, blocks deletion when tasks still reference the group, and removes the record from
  the database when safe.【F:backend/charts/routes.py†L51-L67】

### Task lifecycle endpoints

- `GET /api/tasks` supports optional `group_id` filtering so users can scope the dashboard to a specific collection.【F:backend/charts/routes.py†L70-L84】
- `POST /api/tasks` handles file uploads. It validates the request, generates a UUID-based filename, saves the image in a
  per-user subdirectory, creates the task with a `pending` status, and enqueues the background job with both the filesystem path
  and the publicly accessible URL.【F:backend/charts/routes.py†L87-L132】
- `GET /api/tasks/<id>` fetches a single task after confirming ownership.【F:backend/charts/routes.py†L135-L145】
- `DELETE /api/tasks/<id>` removes the database row, deletes the stored image (if present), and returns a confirmation.【F:backend/charts/routes.py†L148-L167】
- `POST /api/tasks/<id>/cancel` transitions active tasks to the `cancelled` state to signal the worker to skip further work.【F:backend/charts/routes.py†L170-L187】
- `POST /api/tasks/<id>/custom-code` saves user-authored code overrides so the SPA can reload customised snippets later.【F:backend/charts/routes.py†L190-L200】
- `POST /api/tasks/<id>/regenerate-code` rebuilds the accessible markup from stored summaries and data points, letting users
  refresh generated HTML/CSS without re-uploading an image.【F:backend/charts/routes.py†L203-L217】

### Background processing pipeline

- `backend/tasks.py` contains a `ChartProcessingWorker` with a thread-safe queue. `worker.start(app)` boots a daemon thread inside
  the Flask app context, while `worker.enqueue` pushes new uploads onto the queue.【F:backend/tasks.py†L13-L46】
- The worker loop loads the task from the database, skips cancelled entries, marks the task as `processing`, and calls
  `process_chart`. On success it writes back the generated summary, description, data points, table data, accessible code, and
  flips the status to `completed`. Exceptions transition the task to `failed` and store the error message.【F:backend/tasks.py†L32-L64】

### Simulated chart analysis and code generation

- `backend/utils/chart_processing.py` stands in for the real cloud pipeline. `simulate_cloud_processing` opens the uploaded image,
  derives deterministic pseudo-random data points (including positions in pixels and percentages), and builds a structured table
  payload.【F:backend/utils/chart_processing.py†L1-L44】
- `build_accessible_code` renders an accessible HTML template: an image wrapped in a focusable container with ARIA attributes and
  invisible buttons positioned over data points for screen reader announcements.【F:backend/utils/chart_processing.py†L47-L88】
- `process_chart` ties both helpers together and returns the bundle consumed by the worker.【F:backend/utils/chart_processing.py†L91-L95】

## Front-end implementation details

### Application bootstrap and shared state

- `frontend/src/main.js` mounts the Vue application, sets up Pinia, restores persisted authentication data via the auth store,
  and registers the router.【F:frontend/src/main.js†L1-L17】
- The Pinia auth store (`frontend/src/stores/auth.js`) persists the JWT and user profile in `localStorage`, automatically attaches
  the token to Axios, and exposes actions for login, registration, password changes, and logout. An `initialise` helper replays
  the stored token when the SPA boots or routes change.【F:frontend/src/stores/auth.js†L1-L39】
- The router defines guarded routes for the dashboard and task detail screens, redirecting unauthenticated users to the login
  form and preventing logged-in users from revisiting auth screens.【F:frontend/src/router/index.js†L1-L37】

### Authentication views

- **LoginView** displays a styled form that submits credentials to the auth store, handles redirects after successful login, and
  surfaces API errors inline.【F:frontend/src/components/LoginView.vue†L1-L76】
- **RegisterView** collects name, email, and password, invokes the registration action, and shows success/error feedback before
  redirecting users back to the login page.【F:frontend/src/components/RegisterView.vue†L1-L78】

### Dashboard workspace

`frontend/src/components/DashboardView.vue` orchestrates most user workflows:

- **User panel** — shows the authenticated user's profile, provides logout, and toggles an inline password change form that calls
  the auth store's `changePassword` action and reports status messages.【F:frontend/src/components/DashboardView.vue†L3-L85】【F:frontend/src/components/DashboardView.vue†L203-L234】
- **Group management** — loads the user's groups, lets them create new ones, and filter the task list by selected group. Feedback
  messages summarise API responses.【F:frontend/src/components/DashboardView.vue†L23-L72】【F:frontend/src/components/DashboardView.vue†L130-L178】
- **Task upload** — handles file selection, binds optional group assignment, submits multipart form data to the `/api/tasks`
  endpoint, and refreshes the task list once the worker starts processing.【F:frontend/src/components/DashboardView.vue†L88-L178】
- **Task list** — fetches tasks (optionally filtered), renders responsive cards with status chips, summaries, and action buttons
  for viewing details, cancelling in-progress work, or deleting records entirely.【F:frontend/src/components/DashboardView.vue†L180-L312】

### Task detail experience

- `frontend/src/components/TaskDetailView.vue` pulls a single task record, shows the generated summary, preview image, and
  structured table data.【F:frontend/src/components/TaskDetailView.vue†L1-L55】
- The code editor area loads either the generated snippet or any previously saved custom code. Users can reset to the baseline,
  save custom HTML (persisted via the backend), or trigger regeneration from existing metadata.【F:frontend/src/components/TaskDetailView.vue†L57-L118】
- A sandboxed iframe renders the current code so users can immediately validate accessibility tweaks. Refreshing the preview
  simply bumps a key to force rerender without reloading the entire page.【F:frontend/src/components/TaskDetailView.vue†L57-L118】

## Background task coordination flow

Bringing the pieces together:

1. A user submits a new chart task via the dashboard. The SPA posts the form to the backend, which stores the image, creates a
   `ChartTask` record, and enqueues a `TaskPayload` for the worker.【F:frontend/src/components/DashboardView.vue†L98-L178】【F:backend/charts/routes.py†L87-L132】
2. The worker thread marks the task as `processing`, calls the simulated analysis pipeline, and updates the database with the
   generated artefacts before marking the task `completed`. Failures flip the status to `failed`.【F:backend/tasks.py†L32-L64】
3. When the user refreshes the task list or opens the task detail page, the SPA fetches the updated record, displays the summary,
   and populates the editor plus preview to facilitate further refinement.【F:frontend/src/components/DashboardView.vue†L117-L178】【F:frontend/src/components/TaskDetailView.vue†L25-L118】

## Persistence and storage model

- Every user sees only their own groups and tasks because all queries filter by `user_id` tied to the JWT identity, and all CRUD
  routes call `_ensure_owner` before returning details or mutating records.【F:backend/charts/routes.py†L16-L25】【F:backend/charts/routes.py†L70-L217】
- Uploaded files live under `<UPLOAD_FOLDER>/<user_id>/`. Deletion endpoints clean up the corresponding file whenever possible to
  avoid orphaned assets.【F:backend/charts/routes.py†L148-L166】
- Generated metadata (summaries, data points, tables, code, and custom overrides) is stored directly on the task row so it can be
  retrieved without recomputing when users revisit tasks later.【F:backend/models.py†L53-L79】

## Extending the system

To replace the simulated pipeline with real services, update `process_chart` to call your cloud APIs and populate the same
response structure (summary, description, data points, table data, and generated code). The rest of the workflow—background queue,
API responses, and front-end rendering—will continue to work without changes.【F:backend/utils/chart_processing.py†L91-L95】
