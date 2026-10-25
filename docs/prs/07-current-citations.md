Title: Cite the newest eligible evidence for current resource state

When multiple scopes establish the same compliant state, verification could cite an older SQL snapshot because format strength outranked recency. Prefer observation time, then evidence strength and deterministic tie-breakers. Independent replica violations still require remediation even when a newer primary read is absent.

Validation: 38 tests pass, including newer direct reads versus older replica snapshots and independent replica drift. All 518 requests still produce valid rows. Public status accuracy remains 32/32; exact step precision/recall rises to 68.39%, field accuracy to 80.04%, and exact sequences remain 6/32. The full run reuses cached free-model results with $0 reported cost.
