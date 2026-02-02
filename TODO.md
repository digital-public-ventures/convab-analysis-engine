# TODOs

- Ensure we're fully agnostic to teh shape of incoming public comments data
- Switch away from paddle as it is a chinese llm and has issues for government use. Consider easyOCR and ensure that image parsing is encapsulated well enough to swap OCR engines easily.
- build QA skill and flow with separate file for "Improvements to facilitate QA" and their implementation, also create a way to resume previous QA bot for validation. Prevent QA bot from complaining about restrictions, instead ask to speculate on what would need to be true for its restrictions not to be a problem. If there need to be changes to make QA easier, it should assign them: "Add two final sections to your report, one about the final status application implementation and another about the status of QA facilitation noting that the QA file restrictions will not be lifted and any file modification must be assigned as new tasks"
- Figure out why schema use case is shortened
- schema prompt should permit the llm at add max_items to categorical arrays (some like stakeholder type might want to be min 1 max 1)
- Make sure entity names end up in entity mentions wherever the author says them (i.e. don't do "Third-Party Debt Collector" if there's a name given)

stakeholder_type (8 labels):

- Consumer Advocacy Organization
- Financial Services Company
- Government/Regulatory Body
- Healthcare Industry Association
- Healthcare Provider
- Individual Patient
- Legal/Policy Expert
- Unknown

vulnerable_population_identifiers (9 labels):

- Chronic Illness Patient
- Low-Income
- Minority/BIPOC
- Senior/Elderly
- Student
- Underinsured
- Uninsured/Underinsured
- Unknown
- Veteran

reported_consumer_harms (10 labels):

- Aggressive Debt Collection
- Bankrupcty/Legal Action
- Bankruptcy/Legal Action
- Confusion Over Payment Terms
- Credit Score Damage
- Deferred Interest Traps
- Discouragement of Care
- Hidden Interest/Fees
- Lack of Financial Assistance Information
- Unknown

policy_recommendations (8 labels):

- Ban Deferred Interest
- Capping Interest Rates
- Credit Reporting Reform
- Enhanced Oversight of Collections
- Mandatory Financial Assistance Screening
- Provider Training/Certification
- Stricter Disclosure Requirements
- Unknown

product_and_entity_mentions (6 labels):

- CareCredit (Synchrony)
- Hospital Billing Department
- MedPut
- Third-Party Debt Collector
- Unknown
- Wells Fargo Health Advantage
