# Discussion refresh — 2026-09-21

Audit: the old partial mixes 500+ lines of inline CSS with global JS and utility
classes. Reply loading only requests page 1; sorting can discard an in-flight
request and leave the list empty. Enter submits unexpectedly, oversized text is
not prevented, and unsuccessful reactions are silent. The API also allowed
access to hidden threads and eagerly evaluated a per-comment reply COUNT.

Backend contract: shared public-target and thread queries; stable ordering;
explicit reply page/count and focus lookup; successful POST returns its public
comment so the frontend can retain open threads. Pending comments stay private.
Author row locks serialize rate limits and reactions, including first submissions.
All public endpoints respect hidden posts/projects, parent moderation and bans.
No model/schema change or existing comment migration/deletion is needed.

Backend validation: 19 interaction tests pass, including >10 replies, deep links,
hidden targets/parents, malformed requests, pending/approved submission, banned
reactions and zero-query serialization after prefetch. Django check and migration
check pass. Further UI and release verification will be recorded after completion.
