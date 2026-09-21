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

UI: one shared project/journal component, token-based external CSS/JS, compact
Telegram entry, readable comment rows, keyboard-accessible reactions and sorting,
reply context/cancel, image preview/removal and full-size lightbox. Enter inserts a
line; Ctrl/Cmd+Enter submits. Server limits, errors and moderation feedback are
visible; text drafts survive a page reload in session-scoped storage. New posts
retain the current discussion instead of discarding open replies. Sorting aborts
stale requests. Reply deep links can load later pages and then earlier replies.
The first comment page is server-rendered and readable without JavaScript.
New labels cover all four locales; existing translations, including xo, are
unchanged. No existing comment data is rewritten.

Local real-browser QA (390x844 and desktop): signed-in text submission and reply,
Enter/Ctrl+Enter behavior, image upload/preview/lightbox/Escape, reactions and like,
14-reply thread pagination and deep link to page 2, top/newest sorting, duplicate
error preserving the draft, reload restoring the draft, blog reuse, empty state,
and Russian mobile layout without horizontal overflow. Local fixture uploads use
isolated media storage and notification dispatch is disabled in the QA runner.

Release gates: 154/154 tests pass; Django system check reports zero issues;
makemigrations --check --dry-run reports no changes; JS syntax and git whitespace
checks pass. SSR regressions cover project and journal in all four locales,
escaped user text/JSON, session ownership and configured composer limits.

Production verification (2026-09-21): release e9ee4d6 (backend d73f67d) pushed to
origin/main and deployed through ./deploy.sh, exit 0, all health checks green.
Origin/main and server HEAD both e9ee4d639d587e134f225ed212b4adb552e2fbeb.
jaysonkhan/nginx active; /health/ returns database/cache OK; no error-priority
jaysonkhan journal entries since release start (09:21:20 UTC).
Eight public SSR routes (UzExam project + journal entry, xo/uz/ru/en) return 200
with localized discussion endpoints. Public list API retains the existing comment.
Served hashed comments.b1157fec4714.css and comments.afdb6157aa7d.js match the
committed source bytes. Real production browser: official Telegram login widget,
existing avatar/image, image dialog/Escape, newest sorting, guest reply prompt
and focus, desktop and 390px Uzbek layout pass; no browser console errors.
Authenticated mutations were exercised only in the isolated local QA environment;
no production test comments or reactions were created. Live Telegram identity
sign-in was not performed. Existing server-manager.sh and server-only untracked
files were preserved; the primary local checkout was left clean and unchanged.
