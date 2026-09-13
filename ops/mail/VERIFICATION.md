# Jayson mail release verification — 2026-09-14

Production mail code: `d37a5059ba143d36912df9892b2ba2fabbf19200`.
Feature `cae3769`, settings/theme follow-up `0d2940e`, phone follow-up `d37a505`.
All three pushed to origin/main; subsequent documentation commit does not require
another runtime deploy. Entry point for each release: `./deploy.sh --mail`.

## Automated / server evidence

- 17 Python/PHP contract tests passed, including transactional identity sync,
  domain/backend boundaries, fan-out/cycle rejection, 2FA gating, original HTML
  option, editor padding, full-height drawer and alias sender checks.
- Seven integration cases passed against **real Roundcube 1.6.19 MIME decoder**
  locally and on server before each release: plain/quoted/encoded names accepted,
  multiple/foreign/deceptive/empty From rejected. No SMTP transport invoked.
- JavaScript and shell syntax checks passed; PHP files linted.
- Django system check: zero issues; `makemigrations --check --dry-run`: no changes.
- SQLite integrity/schema gate passed. First deploy added **39** profiles:
  38 admin aliases + one own primary for the legacy second mailbox. Both repeat
  deploys added **0**. Existing active counts: admin Jayson 39, second Jayson 2,
  UzExam 26. Existing names/signatures/default flags were preserved.
- Postfix, Dovecot, PHP-FPM, nginx and portfolio services active. Strict IMAP
  certificate hostname/peer validation passed.
- Both public login pages returned their own plugin only. SHA256 checks confirmed
  UzExam plugin/config/release and Roundcube program/vendor files unchanged.
- UzExam mail marker stays `dae8eb2bae173f1fcef551293b89572cffe7efc1`.
  Portfolio checkout stays `d260b2c`; no portfolio reload/seed/migration.
- Final backup: `/var/backups/jaysonkhan-mail/20260913T235558Z-d37a5059ba14/`.
  Automatic rollback never overwrites the live SQLite database.
- After final deploy: no PHP-FPM warning/error journal entries; Roundcube error
  log remained at its pre-deploy timestamp (23:28 UTC), no new entries.
  Existing nginx protocol-option/OCSP warnings predate this mail work and remain
  outside its scope; nginx syntax/health checks succeed.

## Browser evidence

Live authenticated Chrome, 1710×929 and 390×844:

- Inbox loads XIVA INK skin, transparent owner mark, local stationery illustration
  and **38** aliases. Search for support returns its single matching alias;
  Escape closes the modal without affecting messages.
- Compose has **39** From options. Selected support alias successfully, then
  restored the original sender without sending or saving a draft.
- Identities has **39** rows; support edit iframe exposes **39** permitted email
  choices and native name/signature fields. No profile was edited during QA.
- Real 2FA form renders 13 inputs in the styled form without page overflow;
  activation, secrets, recovery codes and account settings were not changed.
- Contacts empty state loads the new address-book illustration and contextual
  copy. Settings empty state uses the owner mark, not an unrelated mail image.
- Mobile inbox has no horizontal page overflow. Drawer close uses the Solar
  close-circle mask, and full drawer background computes to XIVA INK
  `oklch(0.155 0.018 268)` in Paper mode too. Native menu remains usable.
- Light/Paper toggle works. Original Ink preference and 1710×929 viewport were
  restored, temporary QA tabs closed. Jayson inbox left available for the owner.
- Jayson browser error log empty. Separate UzExam public page still loads only
  its own stylesheet/plugin (no Jayson branding).

Synthetic local fixtures (no account/mail data):

- Populated compose first line visible: 56px top padding vs 40px toolbar.
- Sanitized white HTML becomes ink/ivory in dark mode. Original-colors button
  restores white; content is unchanged. No external email content was enabled.
- 390px 2FA inputs have 1px borders, wrap with gaps, helper paragraph flows and
  there is no horizontal overflow. Passwords/codes are synthetic only.
- Login verified in Ink and Paper at desktop/phone widths with local mark/fonts.
  Password toggle changes input type to text and back to password; actual saved
  credentials are never inspected. Autofill paint is covered by the CSS contract,
  not an actual saved-password autofill interaction in this QA pass.

No messages were sent/deleted, no real mail body or verification link opened,
no remote-content loading enabled. End-to-end SMTP delivery from an alias was
not exercised; live From selection and server sender authorization were checked.

Selected Imagegen originals and prompts are versioned in `artwork/`; runtime
WebP artwork is approximately 14/18 KB, alpha preserved. Font files are local,
not third-party runtime requests. Local preview server was stopped after QA.
