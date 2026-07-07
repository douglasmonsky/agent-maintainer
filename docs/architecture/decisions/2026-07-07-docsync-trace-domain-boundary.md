# DocSync Trace Authoring Domain Boundary

DocSync now exposes grouped trace authoring commands and claim-level precision
helpers. The Tach domain contract explicitly lists the new `commands.trace` and
`trace.edit` modules, plus the new fingerprint helper dependencies used by
claim and attestation checks.

This keeps DocSync extractable as a sibling package while making the new CLI
authoring surface and trace loader dependencies visible to architecture checks.
