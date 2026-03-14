# Schema Contract

The response analysis schema (`app/schema/prompts/response_schema.json`) defines how the LLM extracts structured data from each public comment. During analysis, each comment is sent to Gemini along with the schema; the model returns a JSON object whose fields match the schema's definitions. The schema is therefore the single source of truth for every field the pipeline produces — it controls what the LLM extracts, how post-processing validates results, and what columns appear in the final output CSV.

## How the runtime uses the schema

The schema is loaded as JSON and its fields are discovered dynamically at runtime. `response_validation.py` iterates over five top-level groups — `enum_fields`, `categorical_fields`, `scalar_fields`, `key_quotes_fields`, `text_array_fields` — and reads `field_name`, constraints, and allowed values from each entry. No field names are hard-coded in the validation or prompt-building logic, so adding, renaming, or removing a field only requires editing the JSON file and (if applicable) updating the dedup step (`app/dedup/tag_dedup.py`). In practice, field-name changes mostly affect the schema JSON and the analysis outputs rather than Python source code.

The schema generator (`schema/generator.py`) can merge additional fields from a per-dataset generated schema into the base schema, keyed by group name. Duplicate `field_name` values are skipped so the base definition always wins.

## Field families

### Enum fields (single-choice strings)

| Field | Purpose |
|-------|---------|
| `stakeholder_type` | Private individual, organization, or government agency |
| `organization_advocacy_type` | Advocacy orientation; `not_applicable` when stakeholder is an individual |

### Categorical fields (multi-select tag arrays)

| Field | Purpose |
|-------|---------|
| `impact_drivers` | What the commenter blames or credits as causing the impact |
| `vulnerable_population_tags` | Vulnerable populations mentioned (empty array when none) |
| `reported_harmful_impacts` | Harms the commenter reports experiencing |
| `reported_beneficial_impacts` | Benefits the commenter reports experiencing |
| `product_or_company_mentions` | Named products or companies |

### Scalar fields (0–10 numeric scales)

| Field | Scale |
|-------|-------|
| `amount_of_impact` | 0 = no impact → 10 = greatest possible impact |
| `impact_sentiment` | 0 = most harmful → 10 = most beneficial |
| `urgency_of_impact` | 0 = low urgency / tangential → 10 = requires immediate attention |

### Key-quotes fields

| Field | Purpose |
|-------|---------|
| `lived_experience_quotes` | Up to 3 direct quotes showing concrete lived experience with harms or benefits. Distinct from `identified_arguments`, which capture causal/conditional claims. |

### Text-array fields (free-text string arrays)

| Field | Purpose |
|-------|---------|
| `individual_name` | Commenter names extracted from the text |
| `organization_name` | Organization names extracted from the text |
| `identified_arguments` | Causal or conditional claims ("if X then Y") |
| `policy_recommendations` | Policy advice, wishes, or recommendations |

## Key design decisions

### `impact_drivers` vs `impact_sentiment` are orthogonal

`impact_drivers` captures **causality** — what the commenter blames or credits. `impact_sentiment` captures **direction** — whether the impact is harmful or beneficial. A commenter can blame "rule/regulation" (driver) while describing either harms (sentiment → 0) or benefits (sentiment → 10). The `impact_drivers` hint explicitly says: *"Do not infer whether the impact is positive or negative — that is captured in impact_sentiment."*

### Empty arrays, not sentinel `"None"` values

`vulnerable_population_tags` uses an empty array `[]` when no populations are mentioned — there is no `"None"` entry in its `required_values`. This avoids ambiguity during deduplication and aggregation where `[]` and `["None"]` would be semantically identical but technically different.

Other categorical fields that may legitimately have nothing to report use `"None or Not Applicable"` as a canonical sentinel value. This is standardised across `reported_harmful_impacts`, `reported_beneficial_impacts`, `product_or_company_mentions`, and `policy_recommendations`. The one exception is `impact_drivers`, which uses `"unclear"` because it always requires at least one value (`minItems: 1`).

### Renamed harm/benefit fields

The original field names `reported_harms_and_impacts` and `reported_benefits` were renamed to `reported_harmful_impacts` and `reported_beneficial_impacts`. The new names make it explicit that each field captures only one direction of impact, and the parallel naming makes the pair easier to reason about in code and analysis.

### Commenter perspective, not analyst inference

Harm and benefit fields capture what the commenter explicitly describes or clearly implies about their own experience. The hints say: *"Include only impacts the commenter reports or clearly experienced, not inferred downstream consequences."* This prevents the LLM from adding harms or benefits the commenter did not assert.

### `urgency_of_impact` measures decision-urgency, not temporality

The scale rates how time-sensitive the issue is for policymakers (0 = tangential, 10 = requires immediate attention), not when the impact occurred. A past harm that demands urgent policy action scores high; an abstract future concern scores low.

### `lived_experience_quotes` vs `identified_arguments`

These fields serve different downstream purposes. `lived_experience_quotes` captures authentic voices for qualitative reports — personal narratives that humanise the issue. `identified_arguments` captures logical causal claims that can be validated or investigated. The same content should not appear in both.

### `maxItems` constraints

Categorical fields have `maxItems` limits (e.g. 5 for `vulnerable_population_tags`, 10 for `reported_harmful_impacts`, 15 for `product_or_company_mentions`). These are tuned based on observed data distributions to prevent excessive token use without losing signal. Adjust them if your dataset has higher per-record cardinality.

## Null tolerance

LLMs occasionally leave individual categorical fields null (~2% observed rate). The analysis pipeline tolerates this within a 5% threshold. Fields are declared `nullable: false` in the schema to push the LLM toward completeness, but post-processing handles residual nulls gracefully.

## Schema generation flow

1. `/schema/{hash}` loads the cleaned CSV and samples head rows plus random rows (capped at ~50K estimated tokens).
2. `SchemaGenerator` sends the sample data and a use-case description to the LLM.
3. The LLM returns a merged schema: base template fields plus domain-specific fields inferred from the data.
4. The schema is cached in `app/data/{hash}/schema/` and reused by `/analyze`.

The runtime schema lives at `app/schema/prompts/response_schema.json`. System and user prompts for schema generation are in `app/schema/prompts/`.
