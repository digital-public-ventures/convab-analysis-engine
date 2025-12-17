#!/bin/bash
# smoke-test.sh: Fast critical-path smoke tests
#
# Purpose: Verify application is "not on fire" - basic functionality works
# Target time: < 30 seconds total execution
# Philosophy: Test critical paths only, not every edge case

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
START_TIME=$(date +%s)

# Test results tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Helper functions
success() {
	echo -e "${GREEN}✅ $1${NC}"
	TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
	echo -e "${RED}❌ $1${NC}"
	TESTS_FAILED=$((TESTS_FAILED + 1))
	FAILED_TESTS+=("$1")
}

info() {
	echo -e "${CYAN}→ $1${NC}"
}

warning() {
	echo -e "${YELLOW}⚠ $1${NC}"
}

run_test() {
	local test_name="$1"
	local test_command="$2"

	TESTS_RUN=$((TESTS_RUN + 1))
	info "Running: $test_name"

	if eval "$test_command" >/dev/null 2>&1; then
		success "$test_name"
		return 0
	else
		fail "$test_name"
		return 1
	fi
}

# Detect project type and run appropriate tests
detect_and_run_tests() {
	cd "$PROJECT_ROOT"

	# Node.js/JavaScript/TypeScript
	if [ -f "package.json" ]; then
		info "Detected Node.js project"

		# Check if smoke test script is defined
		if command -v npm >/dev/null 2>&1 && npm run | grep -q "smoke-test"; then
			run_test "Node.js smoke tests" "npm run smoke-test"
		else
			warning "No 'smoke-test' script found in package.json"
			warning "Add: \"smoke-test\": \"jest tests/smoke/\" to package.json scripts"
		fi
	fi

	# Python
	if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
		info "Detected Python project"

		if [ -d "tests/smoke" ]; then
			if command -v pytest >/dev/null 2>&1; then
				run_test "Python smoke tests" "pytest tests/smoke/ -v --tb=short"
			else
				warning "pytest not found. Install with: pip install pytest"
			fi
		else
			warning "No tests/smoke/ directory found"
			warning "Create smoke tests in tests/smoke/"
		fi
	fi

	# Go
	if [ -f "go.mod" ]; then
		info "Detected Go project"

		if [ -d "smoke" ] || ls *_smoke_test.go >/dev/null 2>&1; then
			run_test "Go smoke tests" "go test ./smoke/... -v -timeout=30s"
		else
			warning "No smoke/ directory or *_smoke_test.go files found"
			warning "Create smoke tests in smoke/ directory"
		fi
	fi

	# Rust
	if [ -f "Cargo.toml" ]; then
		info "Detected Rust project"

		if [ -f "tests/smoke.rs" ]; then
			run_test "Rust smoke tests" "cargo test --test smoke"
		else
			warning "No tests/smoke.rs file found"
			warning "Create smoke tests in tests/smoke.rs"
		fi
	fi

	# Docker/Container tests
	if [ -f "Dockerfile" ]; then
		info "Detected Dockerfile"

		# Check if Docker is running
		if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
			# Only run if we have a docker smoke test script
			if [ -f "scripts/smoke-test-docker.sh" ]; then
				run_test "Docker smoke tests" "./scripts/smoke-test-docker.sh"
			fi
		else
			warning "Docker not available or not running"
		fi
	fi

	# Generic health check (if no specific tests found)
	if [ $TESTS_RUN -eq 0 ]; then
		warning "No language-specific smoke tests found"
		info "Run generic checks..."

		# Check if there's a health endpoint script
		if [ -f "scripts/health-check.sh" ]; then
			run_test "Health check" "./scripts/health-check.sh"
		else
			warning "No smoke tests configured for this project"
			warning "See docs/evaluation/SMOKE.md for setup instructions"
		fi
	fi
}

# Main execution
main() {
	echo ""
	echo "🧪 Running Smoke Tests"
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo ""

	# Run tests
	detect_and_run_tests

	# Calculate execution time
	END_TIME=$(date +%s)
	EXECUTION_TIME=$((END_TIME - START_TIME))

	echo ""
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	echo ""

	# Print summary
	if [ $TESTS_FAILED -eq 0 ]; then
		success "All $TESTS_PASSED smoke tests passed in ${EXECUTION_TIME}s"

		if [ $EXECUTION_TIME -gt 30 ]; then
			warning "Smoke tests took longer than 30s target"
			warning "Consider optimizing slow tests"
		fi

		echo ""
		exit 0
	else
		fail "$TESTS_FAILED of $TESTS_RUN smoke tests failed"
		echo ""
		echo "Failed tests:"
		for test in "${FAILED_TESTS[@]}"; do
			echo -e "  ${RED}✗${NC} $test"
		done
		echo ""
		echo "Fix failing tests before committing"
		echo ""
		exit 1
	fi
}

# Run main function
main "$@"
