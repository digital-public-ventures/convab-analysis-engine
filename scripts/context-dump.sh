#!/bin/bash
# context-dump.sh: Generate comprehensive project context for AI agents
#
# Purpose: Quickly onboard new agents with essential project information
# Output: Markdown document with structure, key files, recent changes, and guidance

set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

info() {
    echo -e "${CYAN}→ $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="${1:-PROJECT_CONTEXT.md}"
MAX_RECENT_COMMITS=20
MAX_FILE_LINES=50

# Navigate to project root
cd "$SCRIPT_DIR"

info "Generating project context dump..."

# Start output file
cat > "$OUTPUT_FILE" <<'EOF'
# Project Context Dump

**Generated**: $(date +%Y-%m-%d\ %H:%M:%S)
**Purpose**: Quick onboarding for AI agents

---

## Project Overview

EOF

# Add project name and description from README
if [ -f "README.md" ]; then
    echo "### Project Name" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    head -1 README.md | sed 's/^# //' >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    echo "### Description" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    # Get first paragraph after title
    sed -n '/^$/,/^$/p' README.md | head -10 >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# Directory structure
cat >> "$OUTPUT_FILE" <<'EOF'

---

## Directory Structure

```
EOF

# Generate tree (limited depth)
if command -v tree &> /dev/null; then
    tree -L 3 -I 'node_modules|__pycache__|.git|dist|build|target|vendor|.venv|venv' >> "$OUTPUT_FILE"
else
    find . -maxdepth 3 -type d -not -path '*/\.*' -not -path '*/node_modules*' -not -path '*/__pycache__*' | sort >> "$OUTPUT_FILE"
fi

cat >> "$OUTPUT_FILE" <<'EOF'
```

---

## Key Documentation Files

EOF

# List documentation files with brief descriptions
echo "### Core Documentation" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

if [ -f "README.md" ]; then
    echo "- **README.md**: Project overview and quick start" >> "$OUTPUT_FILE"
fi

if [ -f "docs/QUICK_START.md" ]; then
    echo "- **docs/QUICK_START.md**: Setup and installation guide" >> "$OUTPUT_FILE"
fi

if [ -d "docs" ]; then
    echo "" >> "$OUTPUT_FILE"
    echo "### Technical Documentation (docs/)" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    for doc in docs/*.md; do
        if [ -f "$doc" ]; then
            filename=$(basename "$doc")
            title=$(head -1 "$doc" 2>/dev/null | sed 's/^# //' || echo "$filename")
            echo "- **$filename**: $title" >> "$OUTPUT_FILE"
        fi
    done
fi

if [ -d "ADRs" ]; then
    echo "" >> "$OUTPUT_FILE"
    echo "### Architecture Decision Records (ADRs/)" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    for adr in ADRs/*.md; do
        if [ -f "$adr" ] && [[ "$adr" != "ADRs/README.md" ]]; then
            filename=$(basename "$adr")
            title=$(head -1 "$adr" 2>/dev/null | sed 's/^# //' || echo "$filename")
            status=$(grep -i "^\\*\\*Status\\*\\*:" "$adr" 2>/dev/null | head -1 || echo "")
            echo "- **$filename**: $title $status" >> "$OUTPUT_FILE"
        fi
    done
fi

if [ -d "temp/notes" ]; then
    echo "" >> "$OUTPUT_FILE"
    echo "### Planning Documents (temp/notes/)" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    if [ -f "temp/notes/ROADMAP.md" ]; then
        echo "- **ROADMAP.md**: Long-term strategic planning" >> "$OUTPUT_FILE"
    fi
    
    if [ -f "temp/notes/NEXT_STEPS.md" ]; then
        echo "- **NEXT_STEPS.md**: Immediate actionable tasks" >> "$OUTPUT_FILE"
    fi
    
    if [ -f "temp/notes/IMMEDIATE_NEXT_STEPS.md" ]; then
        echo "- **IMMEDIATE_NEXT_STEPS.md**: Immediate actionable tasks" >> "$OUTPUT_FILE"
    fi
fi

# Agent-specific files
cat >> "$OUTPUT_FILE" <<'EOF'

---

## Agent Guidance Files

These files contain explicit instructions for AI agents:

EOF

if [ -f ".github/copilot-instructions.md" ]; then
    echo "- **.github/copilot-instructions.md**: GitHub Copilot instructions" >> "$OUTPUT_FILE"
fi

if [ -f ".cursorrules" ]; then
    echo "- **.cursorrules**: Cursor IDE and agent-specific rules" >> "$OUTPUT_FILE"
fi

if [ -f "docs/AGENT_OPERATIONS.md" ]; then
    echo "- **docs/AGENT_OPERATIONS.md**: Multi-agent coordination patterns" >> "$OUTPUT_FILE"
fi

if [ -f "docs/AGENT_SAFETY.md" ]; then
    echo "- **docs/AGENT_SAFETY.md**: Safety guardrails and prohibited operations" >> "$OUTPUT_FILE"
fi

# Recent git activity
if git rev-parse --git-dir > /dev/null 2>&1; then
    cat >> "$OUTPUT_FILE" <<EOF

---

## Recent Changes

**Last $MAX_RECENT_COMMITS commits**:

\`\`\`
EOF
    
    git log --oneline -n "$MAX_RECENT_COMMITS" >> "$OUTPUT_FILE"
    
    cat >> "$OUTPUT_FILE" <<'EOF'
```

### Recent File Changes

```
EOF
    
    git diff --name-status HEAD~5..HEAD 2>/dev/null >> "$OUTPUT_FILE" || echo "(No recent changes)" >> "$OUTPUT_FILE"
    
    echo '```' >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# Current branch and status
if git rev-parse --git-dir > /dev/null 2>&1; then
    cat >> "$OUTPUT_FILE" <<'EOF'

---

## Git Status

**Current Branch**: 
EOF
    git branch --show-current >> "$OUTPUT_FILE"
    
    echo "" >> "$OUTPUT_FILE"
    echo "**Status**:" >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
    git status --short >> "$OUTPUT_FILE" || echo "(Clean)" >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# Technology stack
cat >> "$OUTPUT_FILE" <<'EOF'

---

## Technology Stack

EOF

# Detect languages and frameworks
if [ -f "package.json" ]; then
    echo "### Node.js/JavaScript" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "- **Runtime**: Node.js" >> "$OUTPUT_FILE"
    if command -v node &> /dev/null; then
        echo "- **Version**: $(node --version)" >> "$OUTPUT_FILE"
    fi
    
    # Extract dependencies
    if command -v jq &> /dev/null; then
        echo "- **Key Dependencies**:" >> "$OUTPUT_FILE"
        jq -r '.dependencies | keys[]' package.json 2>/dev/null | head -10 | sed 's/^/  - /' >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
fi

if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    echo "### Python" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    if command -v python3 &> /dev/null; then
        echo "- **Version**: $(python3 --version)" >> "$OUTPUT_FILE"
    fi
    
    if [ -f "requirements.txt" ]; then
        echo "- **Dependencies**: See requirements.txt" >> "$OUTPUT_FILE"
    fi
    
    if [ -f "pyproject.toml" ]; then
        echo "- **Build System**: pyproject.toml (Poetry/PDM/Hatch)" >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
fi

if [ -f "go.mod" ]; then
    echo "### Go" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    if command -v go &> /dev/null; then
        echo "- **Version**: $(go version)" >> "$OUTPUT_FILE"
    fi
    echo "- **Module**: $(head -1 go.mod)" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

if [ -f "Cargo.toml" ]; then
    echo "### Rust" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    if command -v rustc &> /dev/null; then
        echo "- **Version**: $(rustc --version)" >> "$OUTPUT_FILE"
    fi
    echo "- **Project**: $(grep '^name =' Cargo.toml | head -1)" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# Important configuration files
cat >> "$OUTPUT_FILE" <<'EOF'

---

## Configuration Files

EOF

if [ -f ".editorconfig" ]; then
    echo "- **.editorconfig**: Code style configuration" >> "$OUTPUT_FILE"
fi

if [ -f ".prettierrc" ]; then
    echo "- **.prettierrc**: JavaScript/TypeScript formatting" >> "$OUTPUT_FILE"
fi

if [ -f "ruff.toml" ]; then
    echo "- **ruff.toml**: Python linting and formatting" >> "$OUTPUT_FILE"
fi

if [ -f ".pre-commit-config.yaml" ]; then
    echo "- **.pre-commit-config.yaml**: Pre-commit hooks" >> "$OUTPUT_FILE"
fi

if [ -f "Makefile" ]; then
    echo "- **Makefile**: Build and task automation" >> "$OUTPUT_FILE"
fi

if [ -f "docker-compose.yml" ]; then
    echo "- **docker-compose.yml**: Docker services configuration" >> "$OUTPUT_FILE"
fi

# Quick reference of common commands
cat >> "$OUTPUT_FILE" <<'EOF'

---

## Common Commands

EOF

if [ -f "Makefile" ]; then
    echo "### Make Commands" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo '```bash' >> "$OUTPUT_FILE"
    grep '^[a-zA-Z_-]*:' Makefile | sed 's/:.*/ # (see Makefile for details)/' >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

if [ -f "package.json" ]; then
    echo "### NPM Scripts" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo '```bash' >> "$OUTPUT_FILE"
    if command -v jq &> /dev/null; then
        jq -r '.scripts | keys[]' package.json 2>/dev/null | sed 's/^/npm run /' >> "$OUTPUT_FILE"
    else
        echo "npm run <script> # See package.json for available scripts" >> "$OUTPUT_FILE"
    fi
    echo '```' >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# ROADMAP snippet (if exists)
if [ -f "temp/notes/ROADMAP.md" ]; then
    cat >> "$OUTPUT_FILE" <<'EOF'

---

## Current Roadmap Focus

EOF
    echo '```' >> "$OUTPUT_FILE"
    # Extract "Current Focus" section
    sed -n '/## Current Focus/,/##/p' temp/notes/ROADMAP.md | head -20 >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "*Full roadmap: See temp/notes/ROADMAP.md*" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# NEXT_STEPS snippet (if exists)
if [ -f "temp/notes/NEXT_STEPS.md" ]; then
    cat >> "$OUTPUT_FILE" <<'EOF'

---

## Immediate Next Steps

EOF
    echo '```' >> "$OUTPUT_FILE"
    head -30 temp/notes/NEXT_STEPS.md >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "*Full task list: See temp/notes/NEXT_STEPS.md*" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# Footer
cat >> "$OUTPUT_FILE" <<'EOF'

---

## Getting Started as an Agent

1. **Read Core Documentation**:
   - Start with README.md for project overview
   - Check temp/notes/NEXT_STEPS.md for immediate tasks
   - Review ADRs/ for architectural decisions

2. **Understand Agent Guidance**:
   - Read .github/copilot-instructions.md for workflow guidelines
   - Review docs/AGENT_OPERATIONS.md for coordination patterns
   - Check docs/AGENT_SAFETY.md for prohibited operations

3. **Set Up Development Environment**:
   - Follow docs/QUICK_START.md
   - Run `make setup` or equivalent for your language
   - Verify tooling with `make doctor` if available

4. **Before Making Changes**:
   - Check temp/notes/NEXT_STEPS.md for priorities
   - Review related ADRs for context
   - Update NEXT_STEPS.md after completing work

5. **Quality Checks**:
   - Run tests before committing
   - Follow linting/formatting rules
   - Update documentation if behavior changes

---

**Note**: This context dump is a snapshot. For the most up-to-date information, always check the source files directly.
EOF

success "Context dump generated: $OUTPUT_FILE"
info "Size: $(wc -l < "$OUTPUT_FILE") lines"

# Show summary
echo ""
echo "Summary:"
echo "  - Directory structure"
echo "  - Key documentation files"
echo "  - Recent git activity (last $MAX_RECENT_COMMITS commits)"
echo "  - Technology stack"
echo "  - Configuration files"
echo "  - Common commands"
echo "  - Current roadmap and next steps"
echo ""
echo "Use this file to quickly onboard new agents or get project context."
