# TODOs

- Ensure we're fully agnostic to teh shape of incoming public comments data
- Switch away from paddle as it is a chinese llm and has issues for government use. Consider easyOCR and ensure that image parsing is encapsulated well enough to swap OCR engines easily.
- build QA skill and flow with separate file for "Improvements to facilitate QA" and their implementation, also create a way to resume previous QA bot for validation. Prevent QA bot from complaining about restrictions, instead ask to speculate on what would need to be true for its restrictions not to be a problem. If there need to be changes to make QA easier, it should assign them: "Add two final sections to your report, one about the final status application implementation and another about the status of QA facilitation noting that the QA file restrictions will not be lifted and any file modification must be assigned as new tasks"
- Figure out why schema use case is shortened
- schema prompt should permit the llm at add max_items to categorical arrays (some like stakeholder type might want to be min 1 max 1)
- Make sure entity names end up in entity mentions wherever the author says them (i.e. don't do "Third-Party Debt Collector" if there's a name given)
- canonicalize semicolons for tag separation in text fields
- let's check if the test_csv_processing.py test is overlapping with the e2e test and if we find anything, make a plan to remove the redundant code from test_csv_processing.py
- do we need tag fix? if so, have it sort by id
- quality check for short comments
- quality check for missing attachments
- deal with null tolerance
- validate schema outside of test
