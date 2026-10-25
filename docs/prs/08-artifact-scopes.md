Title: Keep screenshot identifiers on their own records

Native extraction could re-read identifiers from the full transcript after leaving a multi-row record unbound, associating unrelated people with its resource. Bind local OCR words by table row or selected panel, stop ownership at activity history, and preserve these bindings through optional model extraction. Windows OCR and Tesseract supply geometry; no cloud call is required.

Validation: 45 tests pass, covering separate row owners, selected-panel scope, rightmost table columns, ambiguous flat text, Tesseract lines, and model/raw-field overrides. All 518 requests still produce valid rows. Public samples retain 32/32 statuses; field accuracy rises to 82.59%, step precision/recall to 72.11%/70.98%, and exact sequences to 7/32. Remaining resource references and coverage assumptions are documented. The full run reuses free-model caches with $0 reported cost.
