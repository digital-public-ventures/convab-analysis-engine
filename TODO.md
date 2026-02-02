# TODOs

- Ensure we're fully agnostic to teh shape of incoming public comments data
- Switch away from paddle as it is a chinese llm and has issues for government use. Consider easyOCR and ensure that image parsing is encapsulated well enough to swap OCR engines easily.
- build QA skill and flow with separate file for "Improvements to facilitate QA" and their implementation, also create a way to resume previous QA bot for validation. Prevent QA bot from complaining about restrictions, instead ask to speculate on what would need to be true for its restrictions not to be a problem. If there need to be changes to make QA easier, it should assign them: "Add two final sections to your report, one about the final status application implementation and another about the status of QA facilitation noting that the QA file restrictions will not be lifted and any file modification must be assigned as new tasks"
- /Users/jim/.global-git-hooks
