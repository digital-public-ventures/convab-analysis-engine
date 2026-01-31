"""Example tests for cfpb-exploration."""

from pathlib import Path


def test_example():
    """Basic example test."""
    assert 1 + 1 == 2


def test_with_fixture(sample_data):
    """Test using conftest fixture."""
    assert sample_data["name"] == "test"
    assert sample_data["value"] == 42


def test_documentation_coverage():
    """Verify key documentation files exist."""
    project_root = Path(__file__).parent.parent.parent

    required_docs = [
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "docs/QUICK_START.md",
        "docs/README.md",
        "ADRs/README.md",
        "AGENTS.md",  # Agent guidance for this project
    ]

    missing_docs = []
    for doc in required_docs:
        if not (project_root / doc).exists():
            missing_docs.append(doc)

    assert not missing_docs, f"Missing documentation files: {missing_docs}"


def test_source_structure():
    """Verify src/ directory structure exists."""
    project_root = Path(__file__).parent.parent.parent
    src_dir = project_root / "src"

    # Find package directories in src/
    package_dirs = [d for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    # Should have at least one package
    assert len(package_dirs) >= 1, f"Expected at least one package in src/, found: {package_dirs}"

    # Each package should have __init__.py
    for package_dir in package_dirs:
        assert (package_dir / "__init__.py").exists(), f"{package_dir.name}/__init__.py should exist"
