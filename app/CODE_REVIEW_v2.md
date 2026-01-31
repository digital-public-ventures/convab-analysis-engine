# Code Review: LLM and Schema Utilities

**Date:** 2026-01-31
**Scope:** Style, structure, and consistency evaluation of `app/llm/` and `app/schema/`
**Priorities:** Legibility, ease of maintenance, consistent conventions

---

## Executive Summary

The `app/llm/` and `app/schema/` packages provide a well-organized LLM integration layer with solid fundamentals: async-first design, rate limiting, token tracking, and structured output generation. The modular separation of concerns (client, rate limiting, cost tracking, prompts) is exemplary. However, there are inconsistencies in configuration management and some architectural patterns that could be improved.

**Overall Assessment:** Strong architecture with good separation of concerns. Primary issues center on configuration duplication and inconsistent data structures.

---

## Structure Overview

```
app/
├── schema/
│   ├── __init__.py               # Package marker (5 lines)
│   ├── generator.py              # Schema generation class (183 lines)
│   └── prompts/
│       ├── __init__.py               # Package marker (9 lines)
│       ├── prompts.py                # Prompt builders (81 lines)
│       ├── system_prompt.txt         # System prompt (20 lines)
│       ├── user_prompt_template.txt  # User prompt template (18 lines)
│       └── response_schema.json      # Structured output schema (118 lines)
└── llm/
    ├── __init__.py           # Package marker (15 lines)
    ├── gemini_client.py      # Gemini API wrapper (232 lines)
    ├── rate_limiter.py       # Async rate limiting (133 lines)
    ├── model_config.py       # Model profiles (39 lines)
    ├── costs.py              # Pricing info (104 lines)
    ├── response_parser.py    # JSON parsing (47 lines)
    └── token_tracking.py     # Usage logging (44 lines)
```

**Total:** ~1,048 lines across 14 files

---

## Strengths

### 1. Clean Module Organization

- Clear separation between LLM infrastructure (`llm/`) and domain logic (`schema/generator.py`)
- Prompts externalized to text files for easy modification without code changes
- JSON schema in separate file enables validation and IDE support

### 2. Async-First Design

- Consistent use of `async/await` throughout the API layer
- `AsyncRateLimiter` with proper concurrency control via semaphore ([rate_limiter.py:29](app/llm/rate_limiter.py#L29))
- Separate `acquire_concurrency()` and rate limit acquisition for fine-grained control

### 3. Comprehensive Rate Limiting

- Sliding window implementation for RPM/TPM ([rate_limiter.py:61-87](app/llm/rate_limiter.py#L61))
- Daily request limit tracking with automatic reset
- Token counting via API before request ([rate_limiter.py:126](app/llm/rate_limiter.py#L126))
- Clear wait time calculations with informative logging

### 4. Token Usage Tracking

- JSONL format for append-only logging ([token_tracking.py:33-44](app/llm/token_tracking.py#L33))
- Cost calculation integrated with usage recording
- Automatic directory creation for output files

### 5. Structured Output Support

- JSON schema-based response validation ([gemini_client.py:155-185](app/llm/gemini_client.py#L155))
- Thinking level configuration with include_thoughts option
- Response parser handles common LLM output formats ([response_parser.py:8-46](app/llm/response_parser.py#L8))

### 6. Prompt Management

- Templates loaded from external files for easy editing
- Clear separation between system and user prompts
- Prompt builder functions abstract formatting details ([prompts.py:43-59](app/schema/prompts/prompts.py#L43))

---

## Issues and Recommendations

### Critical: Duplicate Rate Limit Configuration

**Location:** [model_config.py:24-38](app/llm/model_config.py#L24) and [generator.py:57-61](app/schema/generator.py#L57)

Rate limits are defined in `ModelProfile` but duplicated in `SchemaGenerator.__init__`:

```python
if "flash" in model_id:
    self.rate_limiter = AsyncRateLimiter(rpm=1000, tpm=1_000_000, rpd=10_000)
else:  # pro model
    self.rate_limiter = AsyncRateLimiter(rpm=25, tpm=1_000_000, rpd=250)
```

**Issues:**

- Duplication violates DRY principle
- String matching (`'flash' in model_id`) is fragile
- Updates to rate limits require changes in two places

**Recommendation:** Use `ModelProfile` to create rate limiters:

```python
profile = MODELS.get(model_key)
self.rate_limiter = AsyncRateLimiter(rpm=profile.rpm, tpm=profile.tpm, rpd=profile.rpd)
```

---

### Critical: Duplicate `load_dotenv()` Calls

**Location:** [gemini_client.py:18](app/llm/gemini_client.py#L18) and [generator.py:22](app/schema/generator.py#L22)

Both files call `load_dotenv()` at module import time.

**Issues:**

- `load_dotenv()` is idempotent but redundant calls create confusion
- Side effects at import time complicate testing
- Unclear which module "owns" environment configuration

**Recommendation:** Move `load_dotenv()` to application entry points only, not library modules.

---

### High: Inconsistent Data Structures

**Location:** [costs.py:15-48](app/llm/costs.py#L15) vs [model_config.py:24-38](app/llm/model_config.py#L24)

`costs.py` uses a list of dictionaries:

```python
model_pricing = [
    {'gemini': {'gemini_3_flash': {...}}},
    {'openai': {'gpt_5_2': {...}}},
]
```

`model_config.py` uses a flat dictionary:

```python
MODELS = {
    'flash': ModelProfile(...),
    'pro': ModelProfile(...),
}
```

**Issues:**

- List-of-dicts structure in `costs.py` requires iteration to find pricing
- Different key formats (`gemini_3_flash` vs `flash`)
- Lookup complexity is O(n) in costs.py vs O(1) in model_config.py

**Recommendation:** Align structures. Consider consolidating pricing into `ModelProfile`.

---

### Medium: Bare Exception Type

**Location:** [rate_limiter.py:55](app/llm/rate_limiter.py#L55)

```python
raise Exception(f'Daily Request Limit ({self.rpd_limit}) Exceeded.')
```

**Issues:**

- Bare `Exception` is hard to catch specifically
- Message uses inconsistent capitalization

**Recommendation:** Define a custom exception:

```python
class RateLimitExceededError(Exception):
    """Raised when API rate limits are exceeded."""
    pass

# In acquire():
raise RateLimitExceededError(f'Daily request limit ({self.rpd_limit}) exceeded')
```

---

### Medium: Hard-Coded Default Paths

**Location:** [gemini_client.py:72](app/llm/gemini_client.py#L72), [token_tracking.py:16](app/llm/token_tracking.py#L16)

```python
token_usage_file: str = 'temp/token_usage.jsonl'
```

**Issues:**

- Relative path depends on working directory
- `temp/` directory may not exist
- Same default in two places

**Recommendation:** Use a configuration module or environment variable:

```python
TOKEN_USAGE_FILE = os.environ.get('TOKEN_USAGE_FILE', 'temp/token_usage.jsonl')
```

---

### Low: Model ID Mapping Inconsistency

**Location:** [gemini_client.py:22-26](app/llm/gemini_client.py#L22) vs [costs.py:60-65](app/llm/costs.py#L60)

```python
# gemini_client.py
MODEL_IDS = {
    'flash': 'gemini-3-flash-preview',
    'pro': 'gemini-3-pro-preview',
}

# costs.py
model_map = {
    'gemini-3-flash-preview': ('gemini', 'gemini_3_flash'),
    'gemini-3-pro-preview': ('gemini', 'gemini_3_pro'),
}
```

**Issues:**

- Two different mapping dictionaries for the same models
- `gemini_client.py` maps short names to full IDs
- `costs.py` maps full IDs to internal keys

**Recommendation:** Consolidate into `model_config.py` and add cost information to `ModelProfile`.

---

## Style Consistency Checklist

| Aspect              | Status          | Notes                                               |
| ------------------- | --------------- | --------------------------------------------------- |
| Quote style         | ⚠ Inconsistent | Mix of single and double quotes across modules      |
| Line length         | ✓ Consistent    | Respects limits                                     |
| Trailing commas     | ✓ Consistent    | Used in multi-line structures                       |
| Docstring format    | ✓ Consistent    | Google-style docstrings across modules              |
| Type hints          | ✓ Consistent    | Used everywhere                                     |
| Async naming        | ⚠ Inconsistent | `generate_structured_content` lacks `_async` suffix |
| Private naming      | ✓ Consistent    | `_` prefix for internal functions                   |
| Constant naming     | ✓ Consistent    | `UPPER_SNAKE_CASE`                                  |
| Import organization | ⚠ Inconsistent | `load_dotenv()` called at import time               |

---

## Architecture Observations

### Positive Patterns

1. **Composition over inheritance** - `SchemaGenerator` composes `genai.Client` and `AsyncRateLimiter`
2. **Single responsibility** - Each module has a focused purpose
3. **External configuration** - Prompts in separate files enable non-code changes
4. **Structured output** - JSON schema ensures consistent API responses

### Areas for Improvement

1. **Configuration consolidation** - Model configs, rate limits, and pricing scattered across files
2. **Provider abstraction** - Current design is Gemini-specific while pricing includes non-Gemini models
3. **Error handling** - Mix of exceptions and `(result, None)` return patterns

---

## Testing Considerations

Tests exist for schema generation and prompts (see `app/tests/test_schema_generation.py`), but core LLM utilities still lack direct coverage. Key gaps:

1. **rate_limiter.py** - Sliding window timing, concurrent access, daily reset
2. **gemini_client.py** - Token estimation, error handling, response parsing
3. **response_parser.py** - Markdown stripping, malformed JSON handling
4. **costs.py** - Cost calculation accuracy, missing model handling

---

## Recommendations Summary

### Priority 1 (Address Soon)

1. Remove duplicate rate limit configuration from `app/schema/generator.py`
2. Remove duplicate `load_dotenv()` calls
3. Fix bare `Exception` in rate_limiter.py

### Priority 2 (Next Iteration)

4. Consolidate model configuration (IDs, rate limits, pricing) into one location
5. Add tests for rate limiting and token/cost calculation paths

### Priority 3 (Technical Debt)

6. Refactor `costs.py` data structure to match `model_config.py` pattern
7. Configure paths via environment variables

---

## Conclusion

The LLM and schema utilities demonstrate thoughtful architecture with clear separation of concerns. The async rate limiting implementation is particularly well-designed. The primary technical debt centers on configuration duplication - rate limits, model IDs, and pricing are defined in multiple locations with different structures. Consolidating these into a unified model registry would significantly improve maintainability. The immediate priority should be removing duplicate rate limit definitions and the redundant `load_dotenv()` calls.
