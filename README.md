# Agent Relay

Agent Relay is the application I worked on for Homework 3 of the DataTalksClub AI Dev Tools Zoomcamp 2026.

The goal of this homework was to take an existing application and make it easier to test, package and deploy. I added PostgreSQL persistence, containerized the application, deployed it locally with Kubernetes and created a CI/CD workflow with GitHub Actions.

## How it works

Agent Relay lets two agents exchange tasks through an API.

A sender creates a task for a recipient. The recipient claims the task, processes it and sends the result back through the relay.

Example used during testing:

```text
Input:  hello relay
Output: HELLO RELAY
Status: completed
```

The dashboard can be used to see registered agents, tasks, their status and delivery history.

## What I implemented

For this homework I added:

- live API integration tests
- Docker support
- PostgreSQL persistence
- Docker Compose configuration
- Kubernetes deployment with kind
- persistent storage for PostgreSQL
- readiness checks
- GitHub Actions CI/CD
- deployment verification
- improvements to the Agent Relay dashboard

## Stack

Python, FastAPI, PostgreSQL, Docker, Docker Compose, Kubernetes, kind, GitHub Actions, pytest and uv.

## Run locally

Install the dependencies and run the application:

```bash
uv sync
uv run uvicorn main:app --reload
```

The application is available at:

```text
http://127.0.0.1:8000
```

Check that the API is ready:

```text
http://127.0.0.1:8000/ready
```

## Run with Docker Compose

```bash
docker compose up --build
```

This starts both Agent Relay and PostgreSQL.

To stop the services:

```bash
docker compose down
```

## Tests

Run the test suite with:

```bash
uv run --frozen pytest
```

The live integration test checks the complete communication flow between two agents:

```text
sender -> relay -> recipient -> relay -> sender
```

## Kubernetes

The Kubernetes manifests are stored in the `k8s/` directory.

```text
k8s/
├── config.yaml
├── postgres.yaml
└── relay.yaml
```

After creating the kind cluster and loading the application image, the resources can be deployed with:

```bash
kubectl apply -f k8s/
```

To access Agent Relay locally:

```bash
kubectl port-forward service/agent-relay 8000:8000
```

## CI/CD

The GitHub Actions workflow is located at:

```text
.github/workflows/ci.yml
```

The pipeline runs the tests before deployment. If the tests pass, it builds the Docker image, deploys the application to Kubernetes and verifies that the deployed API is responding correctly.

## Project structure

```text
agent-relay/
├── .github/workflows/ci.yml
├── k8s/
├── Dockerfile
├── compose.yaml
├── dashboard.html
├── database.py
├── storage.py
├── test_live_api.py
└── README.md
```

## Homework

**DataTalksClub — AI Dev Tools Zoomcamp 2026**  
Homework 3: Test, Containerize, and Deploy an AI-Assisted App

## Author

Chakirou KOUDORO
