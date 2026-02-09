# Schema Review: Base Response Analysis Schema

**Date**: February 2026
**Subject**: Review of `app/schema/prompts/response_schema_example.json` (base schema)
**Status**: Analysis complete with recommendations

---

## Executive Summary

The base schema is **well-structured and thoughtfully designed**, with strong patterns for generic applicability. However, there are **clarity, coherence, and conceptual gaps** that could lead to data quality issues at scale. The schema excels at field organization but shows tension between "generic enough to reuse" and "specific enough to be useful."

**Recommendation**: Address the 8 issues below before expanding to new use cases or scaling the number of comments analyzed.

---

## Table of Contents

1. [Critical Issues](#critical-issues)
2. [Coherence & Design Pattern Issues](#coherence--design-pattern-issues)
3. [Questions for Clarification](#questions-for-clarification)
4. [Strengths Worth Preserving](#strengths-worth-preserving)
5. [Next Steps](#next-steps)

---

## Critical Issues

### 1. Semantic Confusion Between `impact_drivers` and `impact_sentiment`

**Location**: Lines 32-38 and 127-135
**Severity**: HIGH

#### Problem

The distinction between what *caused* an impact and whether that impact is *good or bad* is blurred:

- **`impact_drivers`** (line 32-38): "factors... that the commenter identifies as driving the impact"
  - Captures only *cause*, not direction
  - Example: "rule/regulation" could cause either harm or benefit

- **`impact_sentiment`** (line 127-135): 0=most harmful, 10=most beneficial
  - Captures direction, not cause

These are **orthogonal dimensions**: A commenter can blame a "rule/regulation" (driver) while describing either harms (sentiment→0) OR benefits (sentiment→10).

#### Example of Confusion

Comment: *"The new rule prevents debt spirals."*
- Driver: `rule/regulation` ✓
- Sentiment: 10 (beneficial) ✓
- But the schema doesn't explicitly prevent: *"The old rule caused financial harm."*
  - Driver: `rule/regulation` (ambiguous—which rule?)
  - Sentiment: 2 (harmful) ✓

The LLM must infer that *changes* to rules have directional impact, but this isn't explicitly modeled.

#### Recommendation

Add clearer guidance to the `impact_drivers` hint:

```
"hint": "Identify only what the commenter blames or credits as causing the impact.
Do not infer whether the impact is positive or negative—that is captured separately
in impact_sentiment. Examples: 'a new regulation', 'this company's interest rates',
'lack of provider choice'."
```

---

### 2. `impact_sentiment` Scale Direction is Counterintuitive

**Location**: Lines 127-135
**Severity**: MEDIUM

#### Problem

The scale inverts standard conventions:

```
Standard convention (most systems):
0 = very dissatisfied/negative
10 = very satisfied/positive

Your schema:
0 = most harmful impact
10 = most beneficial impact
```

While **technically correct**, the name `impact_sentiment` suggests "feeling" (emotional tone), not "impact direction" (good vs. bad outcome). This can confuse:
- Developers implementing the schema
- LLMs interpreting the hint
- Analysts reviewing the data

#### Example

A commenter who is *angry* (high emotional intensity) about a *beneficial* change would be:
- `impact_sentiment: 10` (beneficial)
- But "sentiment" usually implies emotional valence (anger = negative sentiment)

#### Recommendation

**Option A** (preferred): Rename to `impact_direction`

```json
{
  "field_name": "impact_direction",
  "description": "Direction of the asserted impact (harmful to beneficial)",
  "scale_interpretation": "0 = most harmful impact, 10 = most beneficial impact"
}
```

**Option B**: Swap the scale (less disruptive if data already exists)

```json
{
  "scale_interpretation": "0 = most beneficial impact, 10 = most harmful impact"
}
```

Then update hint to reflect the new direction.

---

### 3. `vulnerable_population_tags` Includes "None" as a Value

**Location**: Lines 44-56
**Severity**: MEDIUM

#### Problem

The schema allows `"None"` as a `required_value` (line 45), which creates ambiguity:

```json
{
  "required_values": ["None", "Low-Income Individuals", "Seniors/Elderly", "Veterans", "Students"],
  "allow_multiple": true,
  "minItems": 0
}
```

**Data quality risk**: When no vulnerable populations are mentioned, should the output be:
- `[]` (empty array)?
- `["None"]` (array with sentinel value)?

These are semantically identical but technically different. This creates problems:

1. **Deduplication**: Are `[]` and `["None"]` the same during tag deduplication?
2. **Aggregation**: Counting "None" mentions vs. empty mentions produces different results
3. **LLM consistency**: Models may inconsistently use `"None"` vs. empty arrays

#### Example from Your Data

If two comments both mention no vulnerable populations:
- Comment A output: `vulnerable_population_tags: []`
- Comment B output: `vulnerable_population_tags: ["None"]`

When you deduplicate or aggregate, these are treated as *different values*, inflating your tag count.

#### Recommendation

**Remove `"None"` from `required_values`.** Use empty array instead:

```json
{
  "field_name": "vulnerable_population_tags",
  "required": true,
  "description": "Types of vulnerable populations mentioned in the comment, including the commenter.",
  "required_values": [
    "Low-Income Individuals",
    "Seniors/Elderly",
    "Veterans",
    "Students"
  ],
  "allow_multiple": true,
  "nullable": false,
  "minItems": 0,
  "hint": "Select all vulnerable populations the commenter explicitly or implicitly mentions. If none are mentioned, leave empty."
}
```

Apply the same fix to:
- `reported_harms_and_impacts` (line 61)
- `reported_benefits` (line 81)
- `product_or_company_mentions` (line 99)

---

### 4. Ambiguous Distinction: `reported_harms_and_impacts` vs. `reported_benefits`

**Location**: Lines 58-94
**Severity**: MEDIUM

#### Problem

The two fields list opposing outcomes, but the hints don't clarify a critical distinction:

**Are these:**
- **Explicitly stated** by the commenter?
- **Inferred** by the analyst/LLM from described experiences?

#### Example: "Care Delay"

Commenter writes: *"I put off my surgery for a month to save money using CareCredit."*

Possible interpretations:
- **Harm frame**: "Care Delay" (postponing medical treatment is harmful)
- **Benefit frame**: "Financial Prudence" (avoided immediate debt burden)
- **Neutral frame**: Neither—it's a trade-off the commenter chose

The schema's current hint (line 75) says *"Select all harms and impacts described"* but doesn't clarify whose perspective we're using:
- Commenter's perspective?
- Public health perspective?
- Clinical perspective?

#### Risk

An LLM might infer "Care Delay" from contextual clues, when the commenter was actually satisfied with the outcome. This would produce:
- Biased counts of "harms" vs. actual commenter sentiment
- Data that doesn't match `impact_sentiment` (e.g., reporting harms but sentiment=8)

#### Recommendation

Clarify in the hint for both fields:

```json
{
  "field_name": "reported_harms_and_impacts",
  "hint": "Select ONLY harms and impacts the commenter explicitly describes or clearly indicates about their own experience. Do not infer downstream health consequences. Focus on what the commenter reports they experienced, not what you believe they should have experienced."
}
```

And add a **note about perspective** in the schema documentation:

```
## Perspective Handling

All outcome fields (reported_harms_and_impacts, reported_benefits) should reflect
the COMMENTER'S reported experience, not the analyst's interpretation of impact.

Example:
- Commenter: "I delayed care to save money"
- CORRECT output: reported_benefits: ["Financial Flexibility"], ignore "Care Delay"
- INCORRECT output: reported_harms_and_impacts: ["Care Delay or Avoidance"]
```

---

### 5. Missing Temporal Dimension in `urgency_of_impact`

**Location**: Lines 137-145
**Severity**: MEDIUM

#### Problem

The field name suggests "urgency" (priority/importance), but the scale measures *when the impact occurs*:

```
Current scale interpretation:
0 = distant future impact
10 = most urgent/immediate impact
```

These are **different concepts**:

| Concept | Definition | Example |
|---------|-----------|---------|
| **Temporal** | When does it occur? | "I lost my house in 2019" (past) vs. "This will happen next month" (future) |
| **Urgency** | How time-sensitive is it for decision-making? | "Bankruptcy is imminent—needs action today" (urgent) vs. "Long-term trend to watch" (not urgent) |

A commenter describing a past harm ("I went into collections in 2018") is:
- Temporally: Past event (score→0)
- Urgency-wise: Could be urgent to report now for policy impact (score→10)

The field conflates these two dimensions, losing information.

#### Recommendation

**Rename to `impact_timeframe`** and clarify the dimension:

```json
{
  "field_name": "impact_timeframe",
  "required": true,
  "description": "When the asserted impact occurs relative to the comment",
  "scale_min": 0,
  "scale_max": 10,
  "scale_interpretation": "0 = impact is happening now or has recently occurred, 10 = impact is projected far in the future",
  "hint": "Rate when the impact described occurs. 0 = present/recent (now, this month, this year), 10 = distant future (5+ years from now). If the commenter describes a past event, score it as 0."
}
```

**Optional**: Add a separate `regulatory_urgency` scalar field if you want to capture "how important is this for policy decisions," but keep it separate from timing.

---

### 6. Unclear Boundaries: `identified_arguments` vs. `representative_narrative_snippets`

**Location**: Lines 149-156 vs. 176-182
**Severity**: MEDIUM

#### Problem

These two fields overlap significantly in purpose:

- **`representative_narrative_snippets`** (149-156): "emotionally-moving aspects... including the commenter's narrative, **core argument**"
- **`identified_arguments`** (176-182): "causal or conditional arguments... 'if X then Y', 'because X, therefore Y'"

An LLM might extract the same content twice:

```
Source comment: "After I defaulted on the medical loan, I lost custody.
It destroyed my family."

Possible duplicate extraction:
- Snippet: "After I defaulted on the medical loan, I lost custody. It destroyed my family."
- Argument: "Default on medical loans → loss of custody"
```

#### Questions This Raises

1. **Are both needed?** Snippet captures *affect/narrative*; argument captures *causal claim*. For policy analysis, which is more valuable?
2. **What if they conflict?** Snippet says "emotional devastation"; argument is "clinical correlation"?
3. **Deduplication challenge**: How do you deduplicate if someone mentions the same argument three times with different emotional framing?

#### Recommendation

**Clarify the PURPOSE of each field** in schema documentation and hints:

```json
{
  "field_name": "representative_narrative_snippets",
  "hint": "Use these to include authentic voices in policy reports. Select 1-3 quotes
  that preserve the commenter's emotional tone and personal narrative. Prioritize
  quotes that humanize the issue and would resonate with policymakers."
},
{
  "field_name": "identified_arguments",
  "hint": "Extract causal claims you can validate or investigate further. These might
  be tested against data, cited in reports, or flagged for further research.
  Focus on 'if X, then Y' relationships relevant to the commenter's impact claim."
}
```

Also add guidance to system prompt:

```
## Field Separation

These fields serve different purposes:

- identified_arguments: For validating empirical claims
- representative_narrative_snippets: For qualitative reports and policymaker engagement

Do not extract the same quote into both fields. If a quote contains both narrative
and causal claim, choose the field that best serves your primary purpose.
```

---

### 7. Inconsistent Use of "None" / "Not Applicable" Across Fields

**Location**: Lines 45, 61, 81, 99 (and others)
**Severity**: MEDIUM

#### Problem

The schema uses *different names* for the same concept across fields:

| Field | "Empty" Representation |
|-------|----------------------|
| `impact_drivers` | `"unclear"` |
| `vulnerable_population_tags` | `"None"` |
| `reported_harms_and_impacts` | `"None"` |
| `reported_benefits` | `"None"` |
| `product_or_company_mentions` | `"None"` |
| `policy_recommendations` | `"None"` AND `"No Change/Maintain Status Quo"` |

This inconsistency causes problems:

1. **Aggregation**: When counting across fields, "unclear" ≠ "None" ≠ "Not Applicable" semantically, even though they mean the same thing
2. **Validation logic**: Post-processing scripts need special cases for each field
3. **LLM confusion**: The model must learn different conventions for different fields
4. **Analysis**: Hard to answer questions like "What percentage of comments mention nothing at all?"

#### Recommendation

**Establish a schema-wide convention** and document it at the top of `response_schema_example.json`:

```json
{
  "schema_name": "Response Analysis Schema",
  "version": "1.0.0",
  "description": "...",
  "null_handling_convention": "When a categorical or multi-select field has no applicable values, use an empty array [] rather than a sentinel value. Exception: enum fields (single-choice) MUST have a value; use 'not_applicable' when appropriate.",
  "enum_fields": [...]
}
```

Then apply consistently:
- **Categorical fields** (multi-select): Use `[]` when nothing applies
- **Enum fields** (single-choice): Use `"not_applicable"` when needed (or define it as an allowed value)

---

### 8. `minItems` and `maxItems` Constraints Feel Arbitrary

**Location**: Lines 53-54, 72-74, 110-111 (and others)
**Severity**: LOW-MEDIUM

#### Problem

The constraints appear to have no documented rationale:

| Field | MaxItems | Justification? |
|-------|----------|---|
| `vulnerable_population_tags` | 5 | ❓ |
| `reported_harms_and_impacts` | 10 | ❓ |
| `product_or_company_mentions` | 15 | ❓ |
| `identified_arguments` | 5 (implicit) | ❓ |

**Why this matters:**
- If set too low: Data loss (commenter mentions 6 companies, only 5 captured)
- If set too high: Wasted tokens (LLM tries to fill quota)
- If undocumented: Hard to defend in audit/publication

#### Example Risk

Your medical payment products experiment likely involves comments mentioning multiple companies (CareCredit, Synchrony, Wells Fargo, Affirm, Klarna, etc.). If a single comment mentions all six but your schema caps at 5, you lose data.

#### Recommendation

**Document and validate `maxItems`:**

1. **Audit your data**: Run statistics on actual outputs
   ```python
   # Pseudo-code
   import json
   max_harms = max(len(row['reported_harms_and_impacts']) for row in analysis_data)
   max_products = max(len(row['product_or_company_mentions']) for row in analysis_data)
   print(f"Max harms mentioned in a single comment: {max_harms}")
   print(f"Max products mentioned in a single comment: {max_products}")
   ```

2. **Set maxItems to P99 (99th percentile) of observed data**, plus buffer

3. **Document in schema**:
   ```json
   {
     "field_name": "reported_harms_and_impacts",
     "maxItems": 10,
     "maxItems_rationale": "P99 of observed comments mention ≤8 distinct harms. Set to 10 to allow flexibility without excessive token waste."
   }
   ```

---

## Coherence & Design Pattern Issues

### Summary

Beyond the critical issues above, the schema has some **broader design inconsistencies** worth addressing:

| Issue | Impact | Priority |
|-------|--------|----------|
| Different "empty" sentinels across fields | Aggregation complexity | MED |
| Conflation of temporal vs. urgency | Lost analytical dimension | MED |
| Unclear perspective (analyst vs. commenter) | Potential bias in outcomes | MED |
| Undocumented constraint rationales | Data loss risk, maintainability | LOW |

These are addressed in detail in the Critical Issues section above.

---

## Questions for Clarification

Before finalizing the schema, consider:

### 1. Generic vs. Domain-Specific Intent

**Current state:**
- Base schema (`response_schema_example.json`): Generic, works for any comments
- Generated schema (from your experiment): Domain-specific, adds medical payment product fields

**Questions:**
- Is the *goal* to keep the base schema truly domain-agnostic?
- Or should it capture common extraction targets (like "company_mentions")?
- How many times will you reuse this schema? One use case, or many?

**Implication:** If you're building a reusable platform, generic is better. If this is medical-focused, you could be more specific.

### 2. How Do You Handle Conflicting Stakeholder Perspectives?

**Example comment:**
> "The new rule prevents debt spirals, but healthcare providers are furious because it limits their financing options."

**Current schema limitation:** You have `impact_sentiment` (0-10, must pick one), but this comment contains:
- Sentiment: Beneficial (for patients) AND Harmful (for providers)
- Drivers: Both "rule/regulation" and "provider incentives"

**Questions:**
- Should you split into multiple records (one per perspective)?
- Add a `stakeholder_perspective_on_impact` field?
- Create a `conflicting_perspectives` flag?

### 3. How Are You Handling the ~2% Null Rate?

**From your memory notes:** "LLMs occasionally leave individual categorical fields null (~2% rate)"

**Current schema:** `nullable: false` everywhere

**Questions:**
- Is this null rate acceptable?
- Do you post-process nulls (fill with empty array, or flag for review)?
- Should you change `nullable: true` for some fields where nulls are expected?

### 4. Are `suggested_values` Actually Used in Prompts?

**Current structure:**
```json
{
  "required_values": [...]   // Strict closed set
  "suggested_values": [...]  // Hints to the LLM
}
```

**Questions:**
- Does your prompt template include `suggested_values`?
- Does including suggestions help or constrain the LLM's thinking?
- Have you measured whether suggestions increase or decrease accuracy?

---

## Strengths Worth Preserving

The schema has many **excellent design choices**:

✅ **Clear field categorization** (enum, categorical, scalar, text arrays, quotes)
- Easy to understand the role of each field type
- Clear constraints on what's allowed

✅ **Detailed, explicit hints**
- Examples of how to extract each field
- Guidance on edge cases (e.g., "Use 'unclear' only when...")

✅ **Strict null-handling policies**
- `nullable: false` enforces data completeness
- Reduces downstream ambiguity

✅ **Balanced specificity**
- Not so rigid as to prevent discovery
- Not so loose as to lose signal

✅ **Separation of perspectives**
- `stakeholder_type` + `organization_advocacy_type` enable multi-stakeholder analysis
- `impact_sentiment` decoupled from `impact_drivers` (despite the issue noted above)

✅ **Thoughtful field composition**
- Combining scalar, categorical, and narrative fields supports both quantitative and qualitative analysis
- Enables visualization, pattern discovery, AND authentic reporting

---

## Next Steps

### Immediate (Before Scaling)

1. **Address Critical Issues #1 and #3**
   - Clarify `impact_drivers` semantics (Issue #1)
   - Remove `"None"` from categorical fields (Issue #3)
   - Establish consistent null-handling convention (Issue #7)

2. **Audit Real Data**
   - Check `/Users/jim/sensemaking/app/data/efa267c019c11e33cf61afe5ffcf9d2b1fa8dbdcd987b83e911eeea795812334/analyzed/analysis.csv`
   - Measure null rates, max array lengths, distribution of values
   - Identify any data patterns that violate assumptions

3. **Test LLM Behavior**
   - Run schema validation on 10-20 comments
   - Check for inconsistencies in how Gemini interprets hints
   - Verify that `suggested_values` are actually helping

### Short-term (Before Next Experiment)

4. **Rename fields for clarity**
   - `impact_sentiment` → `impact_direction` (Issue #2)
   - `urgency_of_impact` → `impact_timeframe` (Issue #5)

5. **Validate `maxItems` constraints** (Issue #8)
   - Run statistics on your experiment data
   - Adjust limits based on P99 of observed values
   - Document rationale in schema

6. **Clarify field boundaries** (Issue #6)
   - Update hints for `identified_arguments` vs. `representative_narrative_snippets`
   - Add purpose statements to schema documentation

7. **Document perspective handling** (Issue #4)
   - Add explicit guidance to system prompt
   - Clarify: Are we capturing commenter perspective or analyst inference?

### Long-term (Scaling & Reuse)

8. **Create schema design guidelines** (Issues #7 + overall coherence)
   - Establish convention for null values
   - Define when to add enum vs. categorical fields
   - Document trade-offs (specificity vs. generic reusability)

9. **Answer clarification questions** (see section above)
   - Decide: Generic or domain-specific?
   - Plan for multi-perspective comments
   - Establish data quality thresholds

10. **Build schema versioning & migration**
    - How will you evolve the schema as you learn?
    - Can you auto-map old tags to new categories?
    - How will you handle breaking changes?

---

## Conclusion

Your schema is a **solid foundation** with thoughtful design patterns. The issues identified above are **fixable** with minor clarifications and naming adjustments. Once addressed, this schema will be:

- ✅ Clearer for LLMs to interpret
- ✅ More consistent for analysts to use
- ✅ More suitable for scaling across new use cases
- ✅ More defensible in policy contexts

**Estimated effort to address all issues: 4-6 hours** for updates, testing, and documentation.

---

## Appendix: Schema Issue Summary

| # | Issue | Severity | Field(s) | Fix |
|---|-------|----------|----------|-----|
| 1 | Semantic confusion: cause vs. direction | HIGH | `impact_drivers`, `impact_sentiment` | Clarify hint; explain orthogonality |
| 2 | Counterintuitive scale direction | MED | `impact_sentiment` | Rename to `impact_direction` |
| 3 | "None" as sentinel value | MED | `vulnerable_population_tags`, `reported_harms_and_impacts`, `reported_benefits`, `product_or_company_mentions` | Remove, use `[]` instead |
| 4 | Ambiguous perspective (analyst vs. commenter) | MED | `reported_harms_and_impacts`, `reported_benefits` | Clarify hints; add schema note |
| 5 | Temporal vs. urgency conflation | MED | `urgency_of_impact` | Rename to `impact_timeframe`; clarify scale |
| 6 | Unclear field boundaries | MED | `identified_arguments`, `representative_narrative_snippets` | Add purpose statements; clarify hints |
| 7 | Inconsistent null handling | MED | Multiple fields | Establish convention; apply consistently |
| 8 | Undocumented maxItems | LOW | Multiple fields | Audit data; document rationales |
