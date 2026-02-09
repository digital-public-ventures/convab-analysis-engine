# Makefile for cfpb-exploration
# Cross-platform commands for common development tasks

.PHONY: help test server

# Default target: show help
help:
	@echo "dpv/sensemaking - Available commands:"
	@echo ""
	@echo "  make test        - Run fast tests (excludes slow integration tests)"
	@echo "  make server      - Run API server"
	@echo ""


# Run fast tests (excludes slow integration tests)
test:
	@echo "🧪 Running tests..."
	uv run pytest -vv --durations=0 --durations-min=0.15


# Run API server
server:
	@echo "🚀 Starting API server..."
	uv run uvicorn app.server:app --host 0.0.0.0 --port 8000
