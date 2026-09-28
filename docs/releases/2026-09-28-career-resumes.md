# Career profile and English CV downloads — 2026-09-28

The owner confirmed Consort Group employment from June 2026, work on AI integration and maps in Growz/Bizon, UIC Group from September 2023, and TUIT graduation in 2026. The career copy now follows the refreshed resumes instead of the former broad achievement claims.

- Migration `0023_refresh_confirmed_career` adds Consort Group and corrects timeline dates; existing logos, links and descriptions survive this one-time date update. Missing rows are initialized. AIBA ends in November 2025, matching the existing professional profile.
- The deploy copy seeder updates Uzbek, Russian and English role descriptions and introductions. Existing Khorezm text is preserved, including custom database wording.
- About has the current role, previous experience, education and project context. TaxPay is explicitly described as not publicly released after the department closed.
- Home displays month/year dates and complete descriptions. Person structured data identifies Consort Group as the current employer.
- Home and About offer Software Engineer EN and Mobile Developer EN as separate two-page PDFs. Files use Django's static manifest for cache-safe URLs; browser downloads receive readable filenames.

## Assets

Source: the owner's refreshed files in `/Users/mac/Documents/Resume/`.

| File | SHA-256 |
| --- | --- |
| `jahongir-kuziboev-software-engineer-en.pdf` | `399ad5467d72e4de72cb3257f09f834f2cba12a46082b8841e60a41db437c37a` |
| `jahongir-kuziboev-mobile-developer-en.pdf` | `ee07817b14e29854edae2a4b6c03bdd6105d66edb1c86f4fec1db6b7f7a7228b` |

## Local validation

- Django system check: passed; migration drift: none.
- Full Django suite: 164 tests passed. New coverage verifies repeatable career refresh, preservation of existing dialect copy/assets, corrected dates, and both PDF links on Home/About in all four locales without an admin resume upload.
- `git diff --check`: passed; existing `xo` copy values compared structurally against HEAD and unchanged.
- All four gettext catalogs compiled. Only pre-existing missing-header metadata warnings.
- Chrome: English Home timeline and About content verified; 390px mobile view has no horizontal overflow; both download targets exceed 44px height.

Production verification will be recorded after deployment.
