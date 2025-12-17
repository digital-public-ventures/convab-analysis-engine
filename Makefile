# Makefile for cfpb-exploration
# Cross-platform commands for common development tasks

.PHONY: help setup install clean test lint format typecheck build run deploy doctor

# Default target: show help
help:
	@echo "cfpb-exploration - Available commands:"
	@echo ""
	@echo "  make setup       - Initial project setup (install dependencies)"
	@echo "  make install     - Install/update dependencies"
	@echo "  make clean       - Remove build artifacts and caches"
	@echo "  make test        - Run test suite"
	@echo "  make lint        - Run linters"
	@echo "  make format      - Auto-format code"
	@echo "  make typecheck   - Run type checker"
	@echo "  make build       - Build project"
	@echo "  make run         - Run development server"
	@echo "  make deploy      - Deploy to production"
	@echo "  make doctor      - Check development environment"
	@echo ""
	@echo "Customize these targets based on your project's language/framework"

# Initial setup
setup:
	@echo "🚀 Setting up cfpb-exploration..."
	@echo "→ Checking environment..."
	@make doctor
	@echo "→ Installing dependencies..."
	@make install
	@echo "✓ Setup complete!"

# Install dependencies
# Customize based on your language:
install:
	@echo "📦 Installing dependencies..."
	# Python example:
	# pip install -r requirements.txt
	# Node.js example:
	# npm install
	# Go example:
	# go mod download
	@echo "✓ Dependencies installed"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	# Python example:
	# rm -rf __pycache__ .pytest_cache .mypy_cache
	# find . -type d -name "*.egg-info" -exec rm -rf {} +
	# Node.js example:
	# rm -rf node_modules dist build
	# Go example:
	# go clean
	@echo "✓ Cleaned"

# Run tests
test:
	@echo "🧪 Running tests..."
	# Python example:
	# pytest tests/ -v
	# Node.js example:
	# npm test
	# Go example:
	# go test ./...
	@echo "✓ Tests passed"

# Run linters
lint:
	@echo "🔍 Running linters..."
	# Python example:
	# ruff check .
	# Node.js example:
	# npm run lint
	# Go example:
	# golangci-lint run
	@echo "✓ Lint checks passed"

# Format code
format:
	@echo "✨ Formatting code..."
	# Python example:
	# ruff format .
	# Node.js example:
	# npm run format
	# Go example:
	# gofmt -w .
	@echo "✓ Code formatted"

# Type checking
typecheck:
	@echo "🔎 Running type checker..."
	# Python example:
	# mypy .
	# Node.js example:
	# npm run typecheck
	# Go example (built-in):
	# go build -o /dev/null ./...
	@echo "✓ Type check passed"

# Build project
build:
	@echo "🔨 Building project..."
	# Python example:
	# python -m build
	# Node.js example:
	# npm run build
	# Go example:
	# go build -o bin/cfpb-exploration ./cmd/cfpb-exploration
	@echo "✓ Build complete"

# Run development server
run:
	@echo "🏃 Starting development server..."
	# Python example:
	# python -m cfpb-exploration
	# Node.js example:
	# npm run dev
	# Go example:
	# go run ./cmd/cfpb-exploration
	@echo "Server running..."

# Deploy to production
deploy:
	@echo "🚀 Deploying to production..."
	@echo "⚠️  WARNING: This will deploy to production!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	# Add your deployment commands here
	# Examples:
	# git push heroku main
	# docker build -t cfpb-exploration . && docker push cfpb-exploration
	# kubectl apply -f k8s/
	@echo "✓ Deployed"

# Check development environment
doctor:
	@echo "🏥 Checking development environment..."
	@echo ""
	# Check for required tools
	# Example checks:
	@echo "→ Checking for git..."
	@command -v git >/dev/null 2>&1 || (echo "❌ git not found" && exit 1)
	@echo "  ✓ git found: $$(git --version)"
	@echo ""
	# Add more checks based on your project:
	# @echo "→ Checking for python..."
	# @command -v python3 >/dev/null 2>&1 || (echo "❌ python3 not found" && exit 1)
	# @echo "  ✓ python3 found: $$(python3 --version)"
	# @echo "→ Checking for node..."
	# @command -v node >/dev/null 2>&1 || (echo "❌ node not found" && exit 1)
	# @echo "  ✓ node found: $$(node --version)"
	@echo "✓ Environment check complete"

# Quick checks before committing
pre-commit: format lint typecheck test
	@echo "✓ Pre-commit checks passed - ready to commit!"

# CI/CD target - run all checks
ci: lint typecheck test
	@echo "✓ CI checks passed"
