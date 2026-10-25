Title: Run locally and enforce free-only optional cloud inference

Processes PDFs and screenshots with native text/OCR, adds optional cached local intent embeddings, and connects the terminal audit pipeline with attributable usage reporting. Optional OpenRouter calls accept only free model IDs, enforce zero prices, and never fall back to a paid credential or model.

Validation: paid-route rejection, zero-price request-body checks, cache accounting, native artifact isolation, and the existing identity/time/policy suite. All 94 files were processed locally; 375/518 decisions resolved, with unsupported cases explicitly withheld. No cloud inference call has run.
