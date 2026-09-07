# Food Delivery API

A simple Python FastAPI backend for browsing restaurants, creating food orders,
and tracking their delivery status. The application is designed for learning API
development and cloud deployment concepts, with in-memory storage to keep the
code easy to understand.

The API runs locally with Uvicorn or in a container using the included Dockerfile.
It uses FastAPI and Pydantic for request/response validation, and pytest and HTTPX
for testing. There is no frontend, database, or application authentication.

## Project structure

```text
Food_Delivery_Azure/
├── app/
│   ├── main.py         # FastAPI endpoints, totals, and status transition rules
│   ├── models.py       # Pydantic request/response models and status enum
│   └── data.py         # Sample restaurants, order dictionary, and ID counter
├── tests/
│   └── test_api.py     # API tests with fresh in-memory data for each test
├── requirements.txt   # Application and test dependencies
├── Dockerfile         # Python 3.12 image running Uvicorn on port 8000
├── .gitignore         # Excludes environments, caches, and local settings
└── README.md          # Setup, behavior, and API examples
```

## Install and run

Requires Python 3.10 or newer. The Docker image uses Python 3.12.

Run these commands from the repository directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

On Linux/macOS, activate the environment with `source .venv/bin/activate` instead.
If PowerShell prevents activation, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
and `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload` directly.

API: http://localhost:8000

Swagger UI: http://localhost:8000/docs

OpenAPI schema: http://localhost:8000/openapi.json

The root path `/` has no endpoint; use `/health` to check the running application.

## Run with Docker

With Docker installed and running, execute these commands from the repository
root:

```sh
docker build -t food-delivery-api .
docker run --rm --name food-delivery-api -p 8000:8000 food-delivery-api
```

Stop any local server using port 8000 before starting the container. Open
http://localhost:8000/docs to use the containerized API.

The Dockerfile installs `requirements.txt`, copies the `app` directory, and runs
Uvicorn on `0.0.0.0:8000` without development reload. Tests run locally because
the `tests` directory is not copied into the image.

To stop the container from another terminal:

```sh
docker stop food-delivery-api
```

## Run tests

From `Food_Delivery_Azure`, with the virtual environment active:

```sh
python -m pytest -q
```

Tests use HTTPX's AsyncClient with ASGITransport to call the app directly; a
running server is not required. AnyIO's pytest plugin (installed through
FastAPI/Starlette) runs the async tests using asyncio.

The suite covers health, restaurants, order creation and retrieval, calculated
totals, status progression, cancellation, unknown IDs, and invalid request data.
To also fail the run on warnings:

```sh
python -m pytest -q -W error
```

## Coding standards

- Use four spaces for indentation and keep lines within 88 characters.
- Use `snake_case` for functions and variables, `PascalCase` for classes, and
  `UPPER_CASE` for constants such as `ALLOWED_TRANSITIONS`.
- Add short docstrings to modules, classes, functions, and tests. Explain
  business rules and expected errors where useful; avoid repeating every line.
- Add parameter and return type hints. Pydantic models describe API data;
  flexible dictionaries are reserved for test payloads that include invalid data.
- Group imports as standard library, third-party packages, then local modules.
- Keep validation in Pydantic models and business rules in endpoint functions.
  Use named HTTP status constants in application code and clear error messages.
- Keep functions focused and comments about reasons or constraints. Avoid adding
  layers or dependencies for this small learning project.
- Keep tests independent, cover successful requests and invalid input, and run
  `python -m pytest -q -W error` before submitting changes.

These conventions are maintained manually; no formatter or linter is required.

## API behavior

| Method | Path | Success |
| --- | --- | --- |
| GET | `/health` | 200, `{"status":"healthy"}` |
| GET | `/restaurants` | 200, sample restaurant list |
| POST | `/orders` | 201, created order |
| GET | `/orders/{id}` | 200, order |
| PUT | `/orders/{id}/status` | 200, updated order |

### Example order

Send this JSON body to `POST /orders`:

```json
{
  "customer_name": "John",
  "restaurant_id": 1,
  "items": [
    {"name": "Pizza", "quantity": 2, "price": 250},
    {"name": "Garlic Bread", "quantity": 1, "price": 100}
  ]
}
```

The response includes the generated `id`, `total_amount` of `600`, and initial
`status` of `PLACED`, along with the submitted customer and item details. Use
that returned ID in subsequent GET and PUT requests.

### Validation and errors

Create an order using `customer_name`, `restaurant_id`, and a nonempty `items`
list. Each item needs a nonblank `name`, a positive integer `quantity`, and a
finite, nonnegative `price`. Names are trimmed. Missing or invalid fields return
422. Unknown request fields are rejected, including client-supplied IDs, totals,
or initial statuses. The server calculates `total_amount` from item quantities
and prices and sets the initial status to `PLACED`. Prices are supplied by the
client in this learning API; there is no menu or pricing database.

Unknown restaurants and orders return 404. The sample `is_open` field is
informational; this basic API only checks whether the restaurant exists.

| Status code | Meaning |
| --- | --- |
| 400 | Disallowed order status transition |
| 404 | Order or restaurant does not exist |
| 422 | Missing, empty, or invalid request fields |

### Update an order status

Send this body to `PUT /orders/1/status`, replacing `1` with your order ID:

```json
{"status": "CONFIRMED"}
```

The normal status sequence is:

```text
PLACED → CONFIRMED → PREPARING → READY → OUT_FOR_DELIVERY → DELIVERED
```

Only the next step is allowed. `CANCELLED` is also allowed from `PLACED`,
`CONFIRMED`, `PREPARING`, or `READY`. `DELIVERED` and `CANCELLED` are final.
Repeating the current status succeeds without changing the order. Invalid
transitions return 400; an unrecognized status returns 422.

For example, changing directly from `CONFIRMED` to `DELIVERED` returns 400.
Send separate updates for `PREPARING`, `READY`, `OUT_FOR_DELIVERY`, and finally
`DELIVERED`.

## Sample curl commands

These examples use Bash (Linux/macOS, WSL, or Git Bash). Run them in order against
a freshly started server; the first order has ID 1. On Windows PowerShell, use
Swagger UI for easy JSON requests, or run these examples in Git Bash.

Health:

```sh
curl http://localhost:8000/health
```

Restaurants:

```sh
curl http://localhost:8000/restaurants
```

Create an order (server calculates a total of 500):

```sh
curl -i -X POST http://localhost:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"John","restaurant_id":1,"items":[{"name":"Pizza","quantity":2,"price":250}]}'
```

Get the order:

```sh
curl http://localhost:8000/orders/1
```

Update the status:

```sh
curl -i -X PUT http://localhost:8000/orders/1/status \
  -H 'Content-Type: application/json' \
  -d '{"status":"CONFIRMED"}'
```

## Using Postman

Create requests using the methods and paths in the API table, with
`http://localhost:8000` as the base URL. For POST and PUT requests, send the JSON
examples above with `Content-Type: application/json`.

For a deployed instance, replace the base URL with its reachable backend URL or
configured API gateway URL, including any API path prefix. Cloud resources and
gateway configuration are managed separately from this application code.

## In-memory storage limitations

Orders disappear whenever the process restarts, including development reloads.
Multiple workers or replicas would each have separate order dictionaries; keep
this learning version to one process and one replica. Order IDs also reset on
restart. This application is a learning backend, not a production ordering system.
