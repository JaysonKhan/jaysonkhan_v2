# XIVA INK — jaysonkhan.com Design System (v4)

> **O'zbekcha TL;DR:** Bu hujjat — jaysonkhan.com'ning yagona dizayn qonuni.
> Saytga yoki admin panelga **har qanday yangi narsa qo'shilsa, faqat shu tizim
> ichida qo'shiladi**. Yangi rang, yangi shrift, yangi radius o'ylab topish — taqiqlanadi.
> Token yo'q bo'lsa — token qo'shish taklif qilinadi, lekin avval shu fayl yangilanadi.

This document is the **single source of truth** for any agent (Claude Code,
backend, frontend) or human working on jaysonkhan.com UI. Read it fully before
writing a single line of UI code.

Source of the system: the `jaysonkhan-v4` design handoff (claude.ai/design,
2026-06-10), implemented in this repo on the same date.

---

## 0. The Prime Directive

**Everything new must look like it was always here.**

Before adding any UI:
1. Find an existing component/pattern in this doc or in `static/css/site.css` that does 80% of the job. Extend it.
2. Use **only** the CSS custom properties in `static/css/tokens.css`. Never hardcode colors, fonts, radii, easings.
3. If a token genuinely doesn't exist, **add it to `tokens.css` AND document it here** — in the same commit.
4. New UI text must exist in **all 4 languages** (`xo`, `uz`, `ru`, `en`) — via `{% trans %}` (locale/*.po) or modeltranslation fields. No hardcoded strings.

If you violate any of these, the work is not done.

---

## 1. File Map (production)

```
backend/static/css/tokens.css        ← ALL design tokens + base classes. THE law.
backend/static/css/site.css          ← web components/pages (+ legacy utility shim
                                       for partials/interactions.html — don't reuse)
backend/presentation/web/templates/web/   ← SSR templates (base, home, pages, partials)
apps/core/static/admin/css/editorial.css ← admin (Unfold) XIVA INK overlay
apps/core/static/admin/js/theme-bootstrap.js ← forces single dark scheme in admin
```

Fonts load via `<link>` in `base.html` (web) and `@import` in `editorial.css` (admin):
**Schibsted Grotesk** + **IBM Plex Mono**. Never import another family.

---

## 2. Color Tokens — the only palette

Universal single scheme (no light/dark toggle — one theme pleasant day & night).
Deep desert-night ink + warm cream text + two Khiva accents.

| Token | Value | Use |
|---|---|---|
| `--bg-0` | `oklch(0.185 0.018 268)` | page background |
| `--bg-1` | `oklch(0.215 0.018 268)` | raised surface / band sections |
| `--bg-2` | `oklch(0.245 0.02 268)` | cards-on-card, hover rows, active nav |
| `--bg-3` | `oklch(0.285 0.022 268)` | strongest surface, bar-chart tracks |
| `--ink-deep` | `oklch(0.155 0.018 268)` | footer, admin sidebar, log consoles |
| `--fg-0` | `oklch(0.955 0.012 85)` | headlines, primary text |
| `--fg-1` | `oklch(0.87 0.012 85)` | body text |
| `--fg-2` | `oklch(0.72 0.014 80)` | secondary text |
| `--fg-3` | `oklch(0.56 0.016 75)` | muted labels |
| `--fg-4` | `oklch(0.42 0.016 75)` | ghost numerals, faint hints |
| `--line-1/2/3` | cream @ 9% / 16% / 28% | borders: hairline / control / strong |
| `--accent` | `oklch(0.71 0.135 45)` | **Khiva terracotta** — CTAs, active states, emphasis |
| `--accent-strong` | `oklch(0.64 0.15 42)` | accent hover |
| `--accent-soft` | terracotta @ 14% | accent tinted backgrounds |
| `--on-accent` | `oklch(0.16 0.02 45)` | text on accent fills |
| `--accent-2` | `oklch(0.78 0.095 185)` | **majolica turquoise** — data viz, secondary highlights, metric numbers |
| `--accent-2-soft` | turquoise @ 13% | turquoise tinted backgrounds |
| `--ok` / `--warn` / `--bad` | green / amber / red oklch | status ONLY (never decorative) |

Legacy aliases kept for old partials: `--success/--warning/--danger/--info` → status tokens,
`--accent-rgb` (admin css only). Don't use them in new code.

**Rules**
- Accent ratio: terracotta is the *action* color, turquoise is the *data/info*
  color. Never swap their roles. Never use both on the same element.
- Need a new shade? Derive with `oklch(...)` or `color-mix()` from existing
  tokens. Never introduce a new hue.
- Status colors only ever mean status. A red decorative border is a bug.

---

## 3. Typography

| Token | Family | Role |
|---|---|---|
| `--font-display` | **Schibsted Grotesk** 700 | all headlines (`.display-*`), logo |
| `--font-sans` | Schibsted Grotesk 400–600 | body, UI |
| `--font-mono` | IBM Plex Mono | labels, tags, numbers, code, HUD details |

Classes (use these, don't restyle):

```
.display-xl  clamp(52→110px) w700 ls-0.035em   page heroes only
.display-lg  clamp(40→72px)  w700              CTA banners, article titles
.display-md  clamp(32→52px)  w700              section headings
.display-sm  clamp(24→32px)  w700              card titles, admin page titles
.serif-i     italic w700 (display family)      accent words inside headlines
.eyebrow     mono 11px ls.22em uppercase, terracotta, ::before dash
.mono-label  mono 11px ls.16em uppercase, fg-3 — metadata everywhere
.tag         pill chip, mono 10.5px uppercase, line-2 border
```

**Rules**
- The italic `.serif-i` accent word in a headline is the brand signature —
  one per headline, colored `var(--accent)` when emphasized. The hero version
  gets the turquoise squiggle SVG (see `home.html`).
- Numbers (stats, counters, table values, times) are **always mono**.
- Minimum sizes: body 14px, mono labels 10px. Below that — don't.
- Never import another font family. Ever.

---

## 4. Spacing, Radii, Layout

- Container: `.container` → max-width **1280px**, side padding `clamp(20px, 4vw, 56px)`.
- Vertical rhythm: `.section` → `clamp(72px, 9vw, 130px)` top/bottom.
- Radii: `--r-sm 6px` (inputs inside cards), `--r-md 10px` (inputs, buttons-square), `--r-lg 16px` (cards), `999px` (pills/buttons).
- **All sibling groups use flex/grid + `gap`** — never margin-chains.
- Editorial lists (experience, featured work, blog rows): full-width rows separated by `1px solid var(--line-1)` top borders — not boxed cards.
- Cards (`.card`): `--bg-1` + `--line-1` border + `--r-lg`. Hover: border `--line-2`, optional `translateY(-3px)`.
- Responsive: single breakpoint **900px** (`site.css` bottom block + `.g-2m1/.g-4m2/.hide-m` helpers). Hit targets ≥ 44px on mobile.

---

## 5. Motion

- Easing: always `var(--ease-out)` = `cubic-bezier(0.16, 1, 0.3, 1)`. Durations: hover ~0.3s, reveals 0.8–0.9s.
- Scroll reveal: add class `reveal` (+ optional `transition-delay` stagger ≤ 100ms steps); base.html JS flips to `.in`. Gated behind `prefers-reduced-motion: no-preference` — base style is the visible end-state.
- Hero entrances: `fade-up` class with `animation-delay` 0.05–0.3s.
- Infinite loops allowed only for: `dot-live` pulse, ticker scroll, terminal cursor,
  and the Khiva starfield canvas (home page, rAF; honors `prefers-reduced-motion`). Nothing else loops forever.

---

## 6. Shared patterns — reuse, don't reinvent

| Pattern | Where | Use for |
|---|---|---|
| Aurora (`.aurora` + `.aurora--hero/--page/--cta`) | site.css | section background glow |
| Khiva starfield (`static/js/starfield.js` + `.sf-wrap`, `.*--sf` modifiers) | home only | scroll-morph canvas background — law: [starfield-implementation.md](starfield-implementation.md) |
| `.section-head` | site.css | every web section header (eyebrow + display-md + side action) |
| `.page-hero` | site.css | every inner page top |
| `[data-count]` counter | base.html JS | animated stat numbers |
| `[data-clock]` | base.html JS | UTC+5 live clock |
| `.tag.kind-badge--{web,bot,mobile}` + `Project.kind/kind_label` | site.css + models | project type badge |
| `.atable` | tokens.css | all admin-style tables |
| `.field` | tokens.css | all form inputs (focus = accent border) |
| `.kpi`, `.card`, `.pill`, `.feed` | editorial.css | admin dashboard blocks |

Buttons: `.btn` (ghost pill) / `.btn-primary` (terracotta) / `.btn-sm`. Primary
buttons get a trailing arrow SVG. One primary per view region.

---

## 7. i18n Contract

- 4 languages: `xo` (Xorazm sheva — playful, dialect-true), `uz`, `ru`, `en`.
- UI strings → `{% trans %}` with all four locales filled in `backend/locale/*/django.po`
  (see `backend/scripts/xiva_translations.py` for the v4 batch).
- Content → modeltranslation fields (SiteSettings editorial fields, Project, Post...).
  The approved v4 copy seeder: `manage.py apply_xiva_copy`.
- Adding a key = adding it to **all four** languages in the same edit.
- `xo` tone: warm, dialectal ("gal", "ko'ngil qo'yip") — never mocking, never formal-uz copied.

---

## 8. Admin Panel Patterns (Unfold overlay)

- Single dark-ink scheme, forced via `UNFOLD["THEME"] = "dark"` + theme-bootstrap.js.
- Sidebar: `--bg-0` (ink-deep), active item = `--bg-3` bg + `inset 2px 0 0 var(--accent)` + accent icon.
- Page anatomy: `.page-title` (grotesk 700) + actions right → KPI/`card` grid → content.
- Tables: row hover `--bg-3`, status pills, mono for numbers/dates.
- Charts: turquoise for data series, terracotta for the *primary/today* bar, `--fg-4`/soft tints for the rest.
- Telegram = turquoise iconography, Email = terracotta.

---

## 9. Definition of Done — checklist for ANY new UI

```
[ ] Uses only tokens.css variables (grep your diff for '#' hex colors — must be 0)
[ ] No new font families; headlines use .display-* classes (weight 700 only)
[ ] All strings in 4 languages (po or modeltranslation)
[ ] Reuses section-head/page-hero/card/btn/tag patterns where applicable
[ ] flex/grid + gap (no margin-stacking between siblings)
[ ] Hover/focus states present; focus = accent border
[ ] reveal/fade-up gated by prefers-reduced-motion, base = visible end-state
[ ] Responsive at 900px (single column collapse); hit targets ≥44px
[ ] Numbers/dates in mono
[ ] If a new token/pattern was unavoidable → tokens.css updated AND this doc updated
```

## 10. Forbidden (instant review-reject)

- New hex colors, gradients-as-decoration on cards, rounded-left-border "callout" boxes
- Emoji in UI chrome (content/i18n strings may use them sparingly)
- Light theme, pure black `#000`, pure white `#fff`
- New fonts, italic body text, headline weights other than 700
- Drop shadows as primary elevation (we elevate with borders + bg steps)
- Hardcoded UI strings, single-language additions
- `scrollIntoView` in new code (use `window.scrollTo`)
- Decorative infinite animations
- Tailwind utility classes in new templates (the shim at the bottom of site.css
  exists ONLY for the legacy interactions partial)
