# About UX refresh — 2026-09-21

The profile now places the shared anime portrait next to the introduction. The
same partial is used on home: the original image opens through the existing FLIP
lightbox, with an ordinary image link if JavaScript is unavailable. The dialog
has a name, translated close label, keyboard focus containment and focus return.

Story sections use an editorial heading/text layout with anchor navigation.
Name variants remain in the rendered HTML and structured data, inside a native
`details` disclosure. The leaked multiline Django comment was removed.

At <=900px, language choices live inside the mobile menu with 44px targets so
the menu button remains on screen. No existing biography prose was changed.

Validation: Django system check, migration drift check, 21 focused core/portfolio
tests; real browser at desktop and 390x844, anime-to-original image load,
Escape/focus return, and mobile menu/language choices.
