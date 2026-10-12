# Portfolio facts — checked 2026-09-21

Read-only production aggregates, queried 2026-09-21 around 13:39 Tashkent.
These are dated snapshots, not live counters. No personal records were exported.

| Metric | Exact result | Public display | Definition/source |
|---|---:|---|---|
| UzExam published questions | 85,161 | 85k+ | `questions.Question`, status=published |
| UzExam total question rows | 96,344 | not displayed | Includes 10,516 app_only plus draft/review/retired/archived; do not call all published |
| UzExam registered users | 21,645 | 21k+ | `users.User`, is_staff=False, is_superuser=False; not active users |
| UzExam Flutter apps | 7 | 7 | `mobiles/{ielts,multilevel,sat,dtm,milliy,avtotest,intervyu}`; 2026-09-17 build records in mobiles/CLAUDE.md; not a claim of seven current store approvals |
| EduStats bot users | 53,728 | 53k+ | bot_users COUNT(*) |
| EduStats phone-verified users | 991 | not promoted | phone_verified=1 and nonempty phone_number; old 52k verified claim was incorrect |
| EduStats active university listings | 193 | 193 | universities WHERE is_active=1 |
| EduStats admission coverage | 121 | 121 | distinct non-null university_id in university_admission_history |
| EduStats admission records / years | 55,951 / 2020–2025 | years in detail | coverage differs from the full university directory |

UzExam queried through its production Django ORM with PostgreSQL
`default_transaction_read_only=on`. EduStats queried with SQLite `mode=ro` at the
configured DB path; root and bot .env paths agree. Audience totals are not summed
across products because identities are not deduplicated.

Feature evidence: UzExam mobile session/purchase/writing-assessment contracts in
mobiles/CLAUDE.md (2026-09-16/17); EduStats source-backed education-insights code
and admission schema; Vaygo's web + bot catalog, wishlist/signals and AI sales
assistant in vaygo/CLAUDE.md and its web/apps/{catalog,signals,agent} code. No
sales, conversion, active-user or release-version claims were invented for Vaygo.

`apply_edtech_projects` owns the project summaries, stats and distinct technology
sets. `apply_edtech_founder_copy` owns the matching homepage facts; biography
product facts are in bio_copy.py. Owner explicitly authorized factual corrections
to xo while preserving its voice. Personal career history remains unchanged.

Metric JSON carries `as_of`; SSR and API share localized labels and dates.
Filters/search share one queryset function so pagination cannot switch product
kinds. No new database fields or runtime cross-service dependencies were added.

Validation: full Django suite 142/142, zero system-check or migration-drift
issues. Real browser: desktop/390px, search + empty results, native filters,
Russian API continuation (10 initial mobile cards + 2 appended, correct locale),
project metrics and original-image reveal. Browser console: no errors.
