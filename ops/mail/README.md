# JaysonKhan Mail / XIVA INK

Independent, exact-host Roundcube plugin for `mail.jaysonkhan.com`. Ported from
the verified UzExam mail release `dae8eb2b` (2026-09-14), but no runtime dependency
on the UzExam repository, plugin, assets or private alias file. No portfolio
Django, business data, mail content, credentials, routing or 2FA changes.

## Presentation

- XIVA INK terracotta actions, turquoise information and warm ink surfaces;
  Schibsted Grotesk / IBM Plex Mono self-hosted with OFL licenses. Native system
  fallback covers scripts not present in the source fonts, including Cyrillic.
- First visit defaults to Ink. Native user-selected Paper mode remains available
  for the owner's request for parity with both UzExam modes; this is a mail-only
  exception to the portfolio's single-theme policy. The portfolio is untouched.
- Owner's supplied mark regenerated as a transparent terracotta silhouette,
  used for login, rail, favicon and settings; bespoke stationery/contact artwork.
- Solar icons preserve native accessible labels and fallback glyphs. Scope is
  navigation, toolbars, compose, settings, login and modal actions—not mail text.
- Fixed populated editor top padding, long toolbar/rail labels, split buttons,
  native mobile popovers, raw third-party 2FA inputs and button spacing.
- Autofill preserves palette; password reveal changes only `type`, hides again
  on blur/submit, and never reads/copies/logs the value.
- Dark reading colors style only sanitized HTML DOM, never stored content or
  attachments. Original-colors button preserves author appearance; no inversion,
  no remote image loading or sanitizer changes. Plaintext/code stay monospace.
- New plugin copy: English, Uzbek and Russian (Roundcube's existing locales).
  Portfolio `xo` strings are untouched; Roundcube has no existing `xo` locale.

## Sender sequence and ownership

1. Installer checks reviewed Roundcube **1.6.19**, schema **2022081200**, TLS,
   services and the shared lock. It takes a consistent SQLite backup first.
2. `configure.py` reads current Postfix exact maps, resolves alias chains and
   publishes `/var/lib/jaysonkhan-mail/aliases.json`, root:www-data 0640.
   Only ONE terminal local owner qualifies. Catch-all, cycles, missing/external
   destinations and fan-out routes never grant send-as rights. Postfix is not
   modified; new shared aliases need an explicit ownership review.
3. `sync_identities.py` only adds missing primary/alias profiles for existing
   accounts on IMAP backend `127.0.0.1`. SQLite BEGIN IMMEDIATE + one transaction
   makes repeated runs idempotent. Names, signatures, default flags and historical
   profiles are preserved. Dry-run is the default; installer passes `--apply`.
4. Plugin exposes only the authenticated mailbox's aliases, after full 2FA.
   Identity dropdown/save uses an allowlist. A historical unowned default is not
   preselected in a new message/reply; no stored preferences are rewritten.
5. Final send checks **both** SMTP envelope and exactly one MIME-decoded visible
   From. Forged, foreign or revoked addresses abort before SMTP. Missing export
   grants no aliases; primary remains usable. Wrong IMAP backend grants nothing.

Historical finding: the separate `jaysonkhan@jaysonkhan.com` mailbox had an
`admin@jaysonkhan.com` default identity. Provision its own primary without deleting
the old profile; selection/send guards prevent accidental cross-mailbox sending.

Alias changes: rerun the reviewed mail-only deployment to refresh the private
map and identities. No automated creation of forwarding addresses is provided.

## Checks and deployment

```sh
python3 -m unittest discover -s ops/mail/tests
node --check ops/mail/jaysonkhan_mail/mail.js
bash -n deploy.sh ops/mail/install.sh
backend/venv/bin/python backend/manage.py check
backend/venv/bin/python backend/manage.py makemigrations --check --dry-run
./deploy.sh --mail
```

Use a clean reviewed worktree. `--mail` exits before the portfolio's legacy
auto-stage/deploy path. It tests, checks origin ancestry, pushes the exact commit,
ships only `git archive HEAD ops/mail`, then checks the server RELEASE marker.
No Django restart, seeding, migration or mail vendor upgrade occurs.

Both tenants share `/run/lock/uzexam-mail-deploy.lock` (legacy name intentional).
Backup: `/var/backups/jaysonkhan-mail/<UTC>-<SHA>/`. Installer verifies checksums
of UzExam plugin/config/release and Roundcube program/vendor before completion.
Both public login pages must return the correct isolated branding. Only nginx
and PHP are reloaded. IMAP/Postfix sessions, messages and DNS/routing are untouched.

Rollback a specific feature commit and redeploy `--mail`, or restore the scoped
backup under the same lock. Automatic error rollback restores code/config/private
mapping, **never the live SQLite snapshot**, because sessions/contacts may have
changed since backup. New identity records can remain after failed deployment;
they do not authorize sending without the current verified map. Failed assets
are retained in the backup for recovery and diagnosis.

## Local visual QA

`tests/preview_server.py --vendor <Roundcube 1.6.19 skins/elastic> --port 8767`
serves only local fixtures; it does not proxy mail, authenticate or send requests.
Inspect `/` and `/regressions?theme=dark&view=compose|security|login` plus light,
desktop and 390px phone layouts. Live QA must not send mail, enable 2FA, change
credentials, delete messages, or enable remote email content.

Artwork prompts/provenance: [artwork/PROMPTS.md](artwork/PROMPTS.md).
Fonts: Google Fonts `ofl/schibstedgrotesk`, `ofl/ibmplexmono`; OFL files shipped.
Solar: 480 Design, CC BY 4.0; see `jaysonkhan_mail/assets/ATTRIBUTION.txt`.
