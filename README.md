# QA Chatbot Assessment

A FastAPI-based QA chatbot that uses a local knowledge base and OpenAI models to generate testing-related responses.

## Requirements

* Python 3.13+
* uv
* Docker and Docker Compose (optional)
* OpenAI API key

---

## Environment Configuration

Copy `.env.pattern` and create a `.env` file in the project root.

```bash
cp .env.pattern .env
```

Populate the variables in `.env` with appropriate values.

---

## Running with Docker

Start the application and all required services:

```bash
docker compose up
```

The application will be available at:

```text
http://localhost:8000
```

---

## Running Locally

### Create the data directory

```bash
mkdir -p data
```

### Install dependencies

```bash
uv sync
```

### Start the application

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at:

```text
http://localhost:8000
```

---

## API Documentation

Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI schema:

```text
http://localhost:8000/openapi.json
```

---

## Running Tests

Run the full test suite:

```bash
pytest
```

---
