# Stitchbook

Stitchbook is a small personal Flask application for organizing sewing
patterns, fabric inventory, and sewing projects. A project pairs one pattern
with a required outer fabric and an optional lining fabric. It shows estimated
time and compares required yardage with the fabric on hand, but never changes
inventory automatically.

This MVP intentionally has no accounts, uploads, deployment configuration, or
automatic inventory deduction.

## Set up the project

Python 3.10 or newer is recommended.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Initialize the SQLite database:

```bash
flask --app run init-db
```

The database is stored locally at `instance/sewing.db`. The application also
creates its tables when it starts, so `init-db` is safe to run more than once.

## Run the application

```bash
flask --app run run --debug
```

Open <http://127.0.0.1:5000> in a browser.

## Run the tests

```bash
pytest
```

Tests use a temporary SQLite database and do not change your personal data.

## Optional demo data

To add sample patterns, pieces, fabrics, and projects to an empty database:

```bash
flask --app run seed
```

The seed command refuses to run when the database already contains library or
project data, which prevents accidental duplicates.

To return to a completely empty database:

```bash
flask --app run reset-db --yes
```

That command permanently removes all local application data. Alternatively,
stop the app, delete `instance/sewing.db`, and restart it. The SQLite file is
ignored by git.

## Project structure

```text
sewing-project-tracker/
├── app/
│   ├── __init__.py          # application factory and blueprint registration
│   ├── constants.py         # allowed project statuses
│   ├── helpers.py           # validation, delete checks, yardage comparison
│   ├── models.py            # SQLAlchemy data models and relationships
│   ├── routes/
│   │   ├── dashboard.py
│   │   ├── patterns.py
│   │   ├── fabrics.py
│   │   └── projects.py
│   ├── templates/           # Jinja pages grouped by feature
│   └── static/css/style.css
├── instance/                # local SQLite database (not committed)
├── tests/                   # model, helper, and route tests
├── config.py                # Flask and database configuration
├── run.py                   # application entry point
├── seed.py                  # optional seed and reset CLI commands
├── requirements.txt
└── README.md
```

## Architecture

The application follows one simple request flow:

**Browser → Flask route → SQLAlchemy models → Jinja template**

- **Routes** receive requests, validate form values, read or update model
  objects, and choose a template or redirect.
- **Models** describe the database tables and relationships. Flask-SQLAlchemy
  generates SQL and keeps database access in Python.
- **Helpers** contain small shared rules such as non-negative numeric
  validation, delete checks, and enough-fabric comparisons.
- **Templates** render model data into server-generated HTML.
- **CSS** provides the shared responsive visual design without a front-end
  framework.

Feature routes are divided into blueprints so patterns, fabrics, projects, and
the dashboard are easy to locate. The models remain together in one file so
their relationships are easy to understand.

## Data models and relationships

### Pattern

Stores a pattern's name, notes, estimated hours, required outer yardage,
optional lining yardage, notions, and optional image URL.

A Pattern owns zero or more PatternPieces. It may be referenced by many
Projects. A Pattern cannot be deleted while any Project references it.

`lining_yards_required = None` specifically means that the pattern does not
require lining. A numeric value, including zero, means the pattern has a lining
requirement.

### PatternPiece

Belongs to exactly one Pattern and stores the piece name, cut quantity,
measurements, optional fabric type, notes, and image URL.

PatternPieces are owned children. Deleting an unused Pattern automatically
deletes all of its PatternPieces.

### Fabric

Stores a fabric name, yards available, description, notes, and optional image
URL. Inventory is edited manually.

A Fabric may be used as the outer fabric, lining fabric, or both on Projects.
It cannot be deleted while a Project references it in either role.

### Project

Stores a user-entered name, status, notes, and creation time. It references:

- exactly one Pattern;
- exactly one required outer Fabric;
- zero or one lining Fabric.

The outer and lining foreign keys may reference the same Fabric. Project
estimated time and yardage requirements come from its Pattern rather than being
copied onto the Project.

Allowed statuses are `Planned`, `In Progress`, and `Completed`.

## Important behavior

- Pattern, Fabric, and Project forms validate required fields and reject
  negative numeric values.
- PatternPiece quantity must be at least one.
- Project status is checked against the values in `app/constants.py`.
- Yardage checks are informational: a project can be saved when fabric is
  insufficient.
- If a pattern requires lining, a project may still be saved without selecting
  lining; the project page displays that lining is still needed.
- Fabric inventory is never deducted automatically.
- Deleting a Project does not delete its Pattern or Fabrics.
