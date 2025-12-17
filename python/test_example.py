"""Example tests for cfpb-exploration."""
import os
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
    project_root = Path(__file__).parent.parent

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
        "temp/notes/NEXT_STEPS.md",
        "temp/notes/ROADMAP.md",
    ]

    missing_docs = []
    for doc in required_docs:
        if not (project_root / doc).exists():
            missing_docs.append(doc)

    assert not missing_docs, f"Missing documentation files: {missing_docs}"


def test_source_structure():
    """Verify src/ directory structure exists."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    # Find the actual package directory (should be only one subdirectory in src/)
    package_dirs = [d for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    assert len(package_dirs) == 1, f"Expected exactly one package directory in src/, found: {package_dirs}"

    package_dir = package_dirs[0]
    assert (package_dir / "__init__.py").exists(), "__init__.py should exist"
    assert (package_dir / "__main__.py").exists(), "__main__.py should exist"
