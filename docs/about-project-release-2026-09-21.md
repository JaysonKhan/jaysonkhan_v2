# About and project facts release — 2026-09-21

Runtime release: `e8f018287945f326f2219a1102f3d70a31dadd7a`.
About feature: `4084e98`; catalog/facts feature: `e8f0182`.
Released through `./deploy.sh`, completed 13:53 Tashkent. Both feature commits
are on origin/main and the production checkout; no server source was edited.

- Full local Django suite: 142 passed. Final factual-only xo adjustments and URL
  test cleanup: portfolio and biography tests passed. System check: zero issues;
  makemigrations --check --dry-run: no changes. JS syntax and diff checks pass.
- Production: About and Projects return 200 in xo/uz/ru/en; all three project
  detail pages and /health/ return 200. Russian API returns localized dated stats.
- Desktop and 390px live browser: anime cover opens the real 1122px portrait;
  Escape closes and returns focus; About has no horizontal overflow; project
  search returns only EduStats. No browser console errors observed.
- Production static files match local SHA-256 bytes (prefixes): site.css
  c5e2021966c0fd2b, infinite-scroll.js b900f747316eaaa2, lightbox.js
  e299eda2d9fe555b, project-list.js 1f65c88f839c8099.
- Existing starfield brightness fix remains active: canvas computed opacity 0.6.
- jaysonkhan and nginx active; service error journal after release has no entries.
  Existing server-manager.sh local modification and pre-existing untracked
  server files were preserved. Primary local checkout remains clean/untouched.

This verification-only commit is pushed on codex/about-project-refresh; it does
not change the deployed runtime or require a second service restart.
