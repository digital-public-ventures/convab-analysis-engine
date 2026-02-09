# Schema Updates Summary

**Date**: February 8, 2026
**File Updated**: `app/schema/prompts/response_schema_example.json`
**Status**: Applied all requested changes

---

## Changes Applied

### 1. **Enhanced `impact_drivers` Hint**

- **Change**: Added explicit guidance about not inferring sentiment direction
- **Location**: Line 38
- **New Hint**:
  > "Select one or more drivers that the commenter identifies as causing the impact they assert has occurred or will occur. Identify only what the commenter blames or credits. Do not infer whether the impact is positive or negative—that is captured in impact_sentiment. Use 'unclear' only when the commenter does not specify a driver."

**Rationale**: Clarifies that `impact_drivers` captures _causality_ (what caused it) while `impact_sentiment` captures _direction_ (good or bad). These are orthogonal dimensions.

---

### 2. **Clarified `impact_sentiment` Description and Hint**

- **Change**: Renamed description to emphasize perspective; updated hint for clarity
- **Location**: Lines 128, 133
- **New Description**: "Direction of the asserted impact from the commenter's perspective (harmful to beneficial)"
- **New Hint**:
  > "Rate the direction of impact from the commenter's perspective, where zero indicates the most harmful impact and 10 indicates the most beneficial impact. Consider the commenter's perspective when rating. If the commenter describes a mix of positive and negative impacts, rate the net sentiment."

**Rationale**: Makes clear that we're measuring impact _direction_, not emotional sentiment. Emphasizes commenter's perspective.

---

### 3. **Removed "None" from `vulnerable_population_tags`**

- **Change**: Removed `"None"` from `required_values`; updated hint to clarify empty array use
- **Location**: Lines 44-54
- **Old**: `"required_values": ["None", "Low-Income Individuals", "Seniors/Elderly", "Veterans", "Students"]`
- **New**: `"required_values": ["Low-Income Individuals", "Seniors/Elderly", "Veterans", "Students"]`
- **Updated Hint**: "Select the vulnerable population tags that are explicitly or implicitly mentioned. If no vulnerable populations are mentioned, leave empty."

**Rationale**: LLMs will now use empty arrays `[]` consistently instead of mixed `[]` and `["None"]` representations, improving data consistency in deduplication and aggregation.

---

### 4. **Renamed and Clarified `reported_harms_and_impacts` → `reported_harmful_impacts`**

- **Change**: Renamed field for clarity; updated required_values and hint
- **Location**: Lines 57-74
- **Old Field Name**: `reported_harms_and_impacts`
- **New Field Name**: `reported_harmful_impacts`
- **Old Required Value**: `["None"]`
- **New Required Value**: `["None or Not Applicable"]`
- **New Hint**:
  > "Select all harmful impacts explicitly mentioned by the commenter or clearly implied by their described experiences. Include only impacts the commenter reports or clearly experienced, not inferred downstream consequences. Use 'None or Not Applicable' if no harmful impacts are described."

**Rationale**:

- Clearer field name signals we're only capturing _harmful_ impacts, not all impacts
- Explicit guidance prevents LLM from inferring downstream health consequences
- Canonical sentinel value `"None or Not Applicable"` reduces data quality issues

---

### 5. **Renamed and Clarified `reported_benefits` → `reported_beneficial_impacts`**

- **Change**: Renamed field for consistency; updated required_values and hint
- **Location**: Lines 77-92
- **Old Field Name**: `reported_benefits`
- **New Field Name**: `reported_beneficial_impacts`
- **Old Required Value**: `["None"]`
- **New Required Value**: `["None or Not Applicable"]`
- **New Hint**:
  > "Select all beneficial impacts explicitly mentioned by the commenter or clearly implied by their described experiences. Include only impacts the commenter reports or clearly experienced, not inferred downstream consequences. Use 'None or Not Applicable' if no beneficial impacts are described."

**Rationale**:

- Consistent naming with `reported_harmful_impacts`
- Explicit guidance prevents inference beyond what commenter stated
- Canonical sentinel value improves data consistency

---

### 6. **Standardized Sentinel Values Across Categorical Fields**

- **Change**: Updated `product_or_company_mentions` and `policy_recommendations` to use `"None or Not Applicable"`
- **Location**: Lines 98, 187
- **Fields Updated**:
  - `product_or_company_mentions` (line 98)
  - `policy_recommendations` (line 187)

**Rationale**: Consistent sentinel value across all categorical fields prevents LLM from inserting various formats of "None", "N/A", "Not mentioned", etc. Canonicalizing to `"None or Not Applicable"` improves:

- Post-processing validation
- Deduplication accuracy
- Aggregation consistency
- Data quality metrics

---

### 7. **Redefined `urgency_of_impact` to Measure Actual Urgency**

- **Change**: Changed from temporal dimension to decision-urgency dimension
- **Location**: Lines 136-143
- **Old Description**: "Temporal urgency of the asserted impact (distant to imminent)"
- **New Description**: "Time-sensitivity and urgency of the issue for decision-making or action"
- **Old Scale Interpretation**: `"0 = distant future impact, 10 = most urgent/immediate impact"`
- **New Scale Interpretation**: `"0 = low urgency, tangential to core issues, 10 = high urgency, requires immediate attention or decision"`
- **New Hint**:
  > "Rate how time-sensitive or urgent the commenter's concerns are. 10 means the issue requires immediate attention or action because a decision will have imminent consequences (good or bad). 0 means the comment is tangential to core issues, low-priority, or the commenter is primarily advertising their own business rather than addressing the substantive policy question. Consider whether the commenter is raising a concern that policymakers must address urgently versus making a general point or tangential argument."

**Rationale**:

- Temporal dimension (when does impact occur) ≠ Urgency (how important for decision-making)
- New interpretation aligns with policy analysis: "Does this require urgent attention from policymakers?"
- Allows distinguishing between old harms (high urgency if recently reported) vs. abstract future concerns (low urgency)
- Examples: advertising-heavy comment = 0; bankruptcy pending decision = 10

---

### 8. **Renamed `representative_narrative_snippets` → `lived_experience_quotes`**

- **Change**: Renamed field to be more specific about what we're capturing
- **Location**: Lines 148-154
- **Old Field Name**: `representative_narrative_snippets`
- **New Field Name**: `lived_experience_quotes`
- **Old Description**: "Representative narrative snippets from the comment"
- **New Description**: "Quotes capturing concrete examples of lived experience with harms or benefits"
- **New Hint**:
  > "Select up to 3 direct quotes that capture concrete examples of lived experience with harms or benefits from the commenter's perspective. Prioritize authentic narratives and specific experiences that illustrate the impact. May be empty if the comment lacks substantive narrative content or lived experience examples."

**Rationale**:

- More specific field name clarifies we want _lived experience_, not just "important narrative"
- Distinguishes from `identified_arguments` (which capture logical claims)
- Better aligns with use case: Want authentic voices for policy reports, not abstract assertions
- Helps LLM and analysts understand the field's purpose

---

## Sentinel Value Standardization

**Before**: Fields used inconsistent representations:

- `impact_drivers`: `"unclear"`
- `vulnerable_population_tags`: `"None"`
- `reported_harms_and_impacts`: `"None"`
- `reported_benefits`: `"None"`
- `product_or_company_mentions`: `"None"`
- `policy_recommendations`: `"None"` OR `"No Change/Maintain Status Quo"`

**After**: Standardized to `"None or Not Applicable"`:

- `vulnerable_population_tags`: Empty array when nothing mentioned (no sentinel needed)
- `reported_harmful_impacts`: `"None or Not Applicable"`
- `reported_beneficial_impacts`: `"None or Not Applicable"`
- `product_or_company_mentions`: `"None or Not Applicable"`
- `policy_recommendations`: `"None or Not Applicable"` OR `"No Change/Maintain Status Quo"`
- `impact_drivers`: Still uses `"unclear"` (domain-specific, intentional)

**Impact on Data Quality**:

- ✅ Reduces LLM variability in null representations
- ✅ Simplifies post-processing validation and deduplication
- ✅ Improves aggregation accuracy
- ✅ Makes null rates measurable and consistent

---

## Fields NOT Changed

The following decisions were made to **keep existing behavior**:

### ✓ Kept `minItems` and `maxItems` constraints as-is

- **Rationale**: Your team has manually tuned these based on data distribution and visualization needs
- **Assessment**: Values are data-driven and will be validated against actual output

### ✓ Kept `impact_sentiment` scale direction (0=harmful, 10=beneficial)

- **Rationale**: You prefer consistency with existing data
- **Assessment**: Updated description and hint for clarity instead of swapping scale

### ✓ Kept generic base schema approach

- **Rationale**: Base schema stays generic; merged schema (generated per dataset) becomes domain-specific
- **Assessment**: Supports your workflow of generating new schemas for each comments dataset

---

## Testing Recommendations

Before deploying to new datasets, test these changes:

1. **Sentinel Value Handling**: Verify LLM produces consistent `"None or Not Applicable"` (not various formats)

   - Sample: 5-10 comments with no mentioned companies
   - Check: Does `product_or_company_mentions` consistently output `["None or Not Applicable"]`?

2. **Urgency Scoring**: Validate the new urgency dimension matches your intent

   - Sample: Comments describing old harms vs. pending decisions
   - Check: Do "pending decision" comments get higher urgency than "old story" comments?

3. **Lived Experience Quotes**: Verify LLM prioritizes concrete examples

   - Sample: Comments mixing abstract arguments with personal stories
   - Check: Do extracted quotes focus on lived experience, not policy arguments?

4. **Impact Drivers/Sentiment Orthogonality**: Confirm LLM understands cause ≠ direction
   - Sample: Comments blaming rule/regulation while describing benefits
   - Check: Does `impact_drivers` include "rule/regulation" while `impact_sentiment` > 5?

---

## Schema Version Increment

**Current Version**: 1.0.0
**Recommendation**: Consider incrementing to 1.1.0 (minor release) since changes are backward-incompatible:

- Field renames require updating analysis downstream
- Sentinel value changes affect existing data mappings
- New scale interpretation for `urgency_of_impact` requires re-baseline on existing data

---

## Next Steps

1. **Validate** the updated schema against a sample of 20-30 comments
2. **Test** merged schema generation with new dataset
3. **Re-baseline** any existing analysis that used old field names
4. **Document** the schema changes in your data governance/methodology
5. **Update** any downstream analysis code that references renamed fields:
   - `reported_harms_and_impacts` → `reported_harmful_impacts`
   - `reported_benefits` → `reported_beneficial_impacts`
   - `representative_narrative_snippets` → `lived_experience_quotes`

---

## Summary of Impact

| Aspect          | Before                                                 | After                                                                  | Impact                       |
| --------------- | ------------------------------------------------------ | ---------------------------------------------------------------------- | ---------------------------- |
| **Clarity**     | Ambiguous field boundaries                             | Clear separation (cause/direction, explicit/inferred, logic/narrative) | Better LLM interpretation    |
| **Consistency** | Mixed sentinel values (`"None"`, `"unclear"`, `"N/A"`) | Canonical `"None or Not Applicable"`                                   | Better data quality          |
| **Precision**   | Generic output names                                   | Specific names (harmful/beneficial, lived_experience)                  | Clearer downstream use       |
| **Guidance**    | Generic hints                                          | Detailed, context-specific hints with examples                         | Fewer extraction errors      |
| **Metrics**     | Temporal dimension                                     | Decision-urgency dimension                                             | More policy-relevant scoring |
