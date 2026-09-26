# Help Desk Issue Tracker

[![CI](https://github.com/dalidaguney/help-desk-issue-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/dalidaguney/help-desk-issue-tracker/actions/workflows/ci.yml)

A REST API for managing help desk tickets, users, and comments. Built with FastAPI, SQLAlchemy, and SQLite.

## Features

- User registration and login
- Argon2 password hashing
- JWT authentication with 30-minute access tokens
- Employee and administrator permissions
- Ticket creation, listing, viewing, and updating
- Administrator-only ticket assignment and deletion
- Ticket comments
- Ownership and assignment-based access controls
- Ticket status and priority validation
- Interactive Swagger API documentation
- SQLite persistence
- Docker image running as a non-root user
- Persistent Docker volume and container health check
- GitHub Actions checks for tests and code quality

## Technologies

Python, FastAPI, SQLAlchemy, SQLite, Pydantic, python-jose, pwdlib, python-dotenv, and Uvicorn.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/dalidaguney/help-desk-issue-tracker.git
cd help-desk-issue-tracker
```

### 2. Create and activate a virtual environment

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

For development and automated tests, install:

```bash
python -m pip install -r requirements-dev.txt
```

### 4. Configure the signing key

Run this command once from the project directory to create a local `.env` file with a randomly generated key:

```bash
python -c "from pathlib import Path; import secrets; Path('.env').open('x').write('SECRET_KEY=' + secrets.token_hex(32) + '\n'); print('.env created')"
```

The command will not overwrite an existing `.env` file.

Keep the key private. The `.env` file is excluded from Git. Changing the key invalidates existing access tokens.

### 5. Start the API

Run from the project directory:

```bash
uvicorn app:app --reload
```

The application creates its database tables on startup. SQLite data is stored in `helpdesk.db` in the current working directory.

- API: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs

The reload option is intended for local development.

## Run with Docker

Create `.env` as described above, then run:

```bash
docker compose up --build
```

Open:

- API: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Stop the containers with:

```bash
docker compose down
```

The named Docker volume keeps the SQLite database after the container stops.
Use `docker compose down -v` only when you want to delete that stored data.

## Automated Tests

Install the development dependencies, then run:

```bash
pytest
```

The tests use a separate in-memory database. They do not modify the local
`helpdesk.db` file.

## Using Swagger

1. Open `/docs`.
2. Register an account using `POST /users`.
3. Log in using `POST /login`.
4. Copy the `access_token` value from the response.
5. Click **Authorize** and paste only the token, without quotes or a `Bearer` prefix.
6. Click **Authorize**, then **Close**.
7. Use **Try it out** and **Execute** to test protected endpoints.

Swagger adds the `Bearer` prefix automatically. If the token expires, log in again and authorize with the new token.

## API Endpoints

| Method | Endpoint                        | Description                         |
| ------ | ------------------------------- | ----------------------------------- |
| GET    | `/`                             | View the API status message         |
| GET    | `/health`                       | Check API and database health       |
| POST   | `/users`                        | Register an employee account        |
| POST   | `/login`                        | Receive an access token             |
| GET    | `/me`                           | View the authenticated user         |
| GET    | `/tickets`                      | List accessible tickets             |
| POST   | `/tickets`                      | Create a ticket                     |
| GET    | `/tickets/{ticket_id}`          | View a ticket                       |
| PATCH  | `/tickets/{ticket_id}`          | Update a ticket                     |
| DELETE | `/tickets/{ticket_id}`          | Delete a ticket as an administrator |
| POST   | `/tickets/{ticket_id}/comments` | Add a comment                       |
| GET    | `/tickets/{ticket_id}/comments` | List comments                       |

## Example Requests

### Register a user

`POST /users`

```json
{
  "username": "demo_employee",
  "email": "demo@example.com",
  "password": "LocalDemoPassword123!"
}
```

Use a separate password for your own account.

### Log in

`POST /login`

```json
{
  "username": "demo_employee",
  "password": "LocalDemoPassword123!"
}
```

### Create a ticket

`POST /tickets`

Requires authentication.

```json
{
  "title": "Login page error",
  "description": "Users cannot sign in to the application.",
  "priority": "high"
}
```

### Update a ticket

`PATCH /tickets/{ticket_id}`

```json
{
  "status": "in_progress"
}
```

Fields omitted from a PATCH request remain unchanged.

### Add a comment

`POST /tickets/{ticket_id}/comments`

```json
{
  "body": "The login issue is being investigated."
}
```

## Ticket Values

Supported priorities:

- `low`
- `medium`
- `high`

Supported statuses:

- `open`
- `in_progress`
- `resolved`
- `closed`

New tickets start with `open` status. The default priority is `medium`.

Explicit `null` values are rejected for title, description, status, and priority during updates. Administrators can set `assigned_to_id` to `null` to remove an assignment.

## Permissions

All new accounts receive the `employee` role. Registration does not allow users to choose administrator permissions.

Employees can:

- Create tickets
- View and update tickets they created or were assigned
- Add and read comments on accessible tickets

Administrators can:

- Access all tickets and their comments
- Update and assign tickets
- Delete tickets

Create the first administrator from the project directory. The password is
requested securely and is not stored in shell history:

```bash
python manage.py create-admin --username admin --email admin@example.com
```

When using Docker, run:

```bash
docker compose exec api python manage.py create-admin --username admin --email admin@example.com
```

Public registration always creates an employee account, so users cannot grant
themselves administrator permissions.

## Continuous Integration

GitHub Actions runs on every push to `main` and on every pull request. The
workflow installs the development dependencies, checks the code with Ruff, and
runs the automated API tests. A failed check is visible on GitHub before code is
merged.

## Response Codes

- `200`: Successful request
- `201`: Resource created
- `204`: Ticket deleted
- `400`: Username or email already registered
- `401`: Missing, invalid, or expired authentication
- `403`: Insufficient permissions
- `404`: Ticket not found
- `422`: Invalid request data

## Project Structure

```text
help-desk-issue-tracker/
├── .github/workflows/ci.yml
├── .dockerignore
├── .env.example
├── Dockerfile
├── app.py
├── auth.py
├── compose.yaml
├── database.py
├── dependencies.py
├── manage.py
├── models.py
├── schemas.py
├── requirements.txt
├── requirements-dev.txt
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── .gitignore
└── README.md
```

Local files created during setup or use include `.env`, `.venv/`, and `helpdesk.db`. These are excluded from Git.

## Project Status

This portfolio project has a working API, authentication and authorization,
automated tests, code-quality checks, container packaging, persistent container
storage, health monitoring, and continuous integration. A graphical user
interface is outside the current project scope.
