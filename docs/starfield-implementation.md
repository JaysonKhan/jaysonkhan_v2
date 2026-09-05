# Xiva yulduz turkumi foni — implementatsiya hujjati

> Fayl: `js/starfield.jsx` · Komponent: `<KhivaStarfield />` · Holat: ishlab turibdi (v1.1 — "yorqin" reviziya)

Scroll qilganda yulduzlar (canvas zarralari) Ichan-Qal'a obidalarini chizadi va bir obidadan
ikkinchisiga **yulduzlar harakati orqali** kino kabi morph bo'ladi. Hech qanday rasm ishlatilmaydi —
hamma narsa real vaqtda chiziladi.

---

## 1. Umumiy arxitektura

```
scroll pozitsiyasi (0..1)
        │
        ▼
shapePos = progress × (shakllar soni − 1)     ← silliqlash: cur += (target−cur)×0.065
        │
        ▼
har bir zarra:  A-shakl nuqtasi ──easing──▶ B-shakl nuqtasi
                (+ galaktik yoy burilishi, + drift, + miltillash)
        │
        ▼
render: chang qatlami → yulduzlar (halo+yadro+nurlar) → turkum chiziqlari → uchar yulduz → sarlavha
```

**5 ta shakl, scroll bo'ylab teng taqsimlangan:**

| # | Shakl | Sahifadagi o'rni |
|---|---|---|
| 0 | Kalta Minor | Hero |
| 1 | Madrasa peshtog'i | Manifest / Metrikalar |
| 2 | Islom Xo'ja minorasi + maqbara | About / Tajriba |
| 3 | Xiva silueti (devor, gumbazlar) | Ishlar / Jarayon |
| 4 | Galaktika spirali | Jurnal / CTA |

## 2. Shakl nuqtalarini olish (`sampleShape`)

1. 640×640 offscreen canvasga obida **oq shtrix chiziqlar** bilan chiziladi
   (`drawKalta`, `drawPortal`, `drawIslomXoja`, `drawSkyline` — line/arch/dome/band primitivlari).
2. `getImageData` orqali alpha > 90 bo'lgan piksellar yig'iladi (har 2px qadam).
3. Ulardan tasodifiy `N` ta nuqta tanlanadi, 0..1 oraliqqa normalizatsiya qilinadi.
4. **Markaz atrofidagi burchak bo'yicha saralanadi** (`sortByAngle`) — shu tufayli
   morph paytida zarralar xaotik kesishmaydi, balki bir tekis "aylanib oqadi".

Galaktika (`galaxyPoints`) piksel-sampling emas: 3 yelkali logarifmik spiral + markaziy yadro
formuladan to'g'ridan-to'g'ri generatsiya qilinadi.

## 3. Zarra tizimi

- Soni: **1800** (desktop) / **560** (mobil, `<768px`; 2026-09-05 gacha 820 — §11).
- Har zarra deterministik hash (`sfHash(i)`) orqali xususiyat oladi:
  - `c` — rang: 84% krem, 9% feruza (`--accent-2` ohangi), 7% terrakota (`--accent` ohangi)
  - `r` — radius 1.0–2.9px, 4% "yirik yulduz" (+2.0)
  - `spd`, `ph` — miltillash tezligi va fazasi
- **Morph**: `ff = clamp((f − h0×0.35) / 0.65)` — har zarra o'z kechikishi bilan uchadi
  (to'da/swarm effekti), `easeInOutQuad` bilan.
- **Galaktik yoy**: to'g'ri chiziq o'rniga perpendikulyar `sin(e·π)×(h1−0.5)×0.22` siljish —
  zarralar egri trayektoriya bo'ylab uchadi.
- **Prujina**: `pos += (target − pos) × 0.085` — scroll to'xtaganda yumshoq joylashadi.

## 4. Render qatlamlari (har kadr)

| Qatlam | Texnika |
|---|---|
| Fon changi | 240 statik mayda yulduz, scroll parallaks (`y −= scrollY×0.045×z`), miltillash |
| Yulduz halosi | 64px radial-gradient sprite, `globalCompositeOperation: "lighter"` (additiv nur); alpha `a·0.5`, o'lcham `r·(5.0+glint·5.5)·haloK` (§11) |
| O'tkir yadro | `arc()` to'liq alpha bilan — yulduz tiniq ko'rinadi |
| Diffraksiya nurlari | `r > 2.9` (faqat 4% «yirik» yulduz) yoki `glint > 0.45` paytida 4 tomonlama ingichka kross, alpha `a·0.35` (2.2 chegara yulduzlarning 39%ini qamrab olardi — §11) |
| Chaqnash (glint) | `sin^28` puls — yulduz vaqti-vaqti bilan yarqiraydi |
| Harakat izi (streak) | tezlik > 1.6px bo'lsa orqaga 3.4× chiziq — "oqib o'tish" effekti; alpha `a·0.6` |
| Turkum chiziqlari | har 15-zarra (≈120 langar) orasida `d < 5vmin` bo'lsa ingichka ip; faqat joylashganda (`settle`) |
| Uchar yulduz | 4.5–10.5s intervalda gradient dumli meteor |
| Sarlavha | obida nomi (IBM Plex Mono, 10.5px) o'ng-pastda, integer pozitsiyada paydo bo'ladi |

## 5. Integratsiya (React prototipda)

```jsx
// pages-home.jsx
<main data-screen-label="Home">
  <KhivaStarfield intensity={tweaks.stars ?? 0.85} lines={tweaks.starLines !== false} />
  <div style={{ position: "relative", zIndex: 1 }}>
    {/* barcha seksiyalar */}
  </div>
</main>
```

- Canvas: `position: fixed; inset: 0; z-index: 0; pointer-events: none`.
- Kontent `z-index: 1` o'ramda; yulduzlar ko'rinib turishi uchun uch seksiya foni
  **shaffof** qilingan:
  - ticker: `oklch(0.215 0.018 268 / 0.55)`
  - metrikalar bandi: `oklch(0.155 0.018 268 / 0.62)`
  - tanlangan ishlar: `oklch(0.215 0.018 268 / 0.5)`
- Tweaks: `stars` (0–1 slider), `starLines` (toggle) — `app.jsx` da.

## 6. Unumdorlik va accessibility

- `devicePixelRatio` 2 bilan cheklangan; sprite'lar oldindan keshlanadi (shadowBlur YO'Q).
- Turkum chiziqlari faqat ~120 langar orasida → ≤7k masofa tekshiruvi/kadr.
- Sahifa fonida ishlaydi: `requestAnimationFrame` tab yashiringanda o'zi to'xtaydi.
- `prefers-reduced-motion: reduce` → morph bir zumda (snap), miltillash/streak/meteor o'chadi.
- Route almashganda komponent unmount bo'ladi, `cancelAnimationFrame` + listener tozalanadi.

## 7. Sozlash nuqtalari (tez topish uchun)

| Nima | Qayerda |
|---|---|
| Zarra soni | `var N = mobile ? 560 : 1800` |
| Yorug'lik (2 knob) | `home.html`: `intensity` — har yulduz alfasi (additiv yig'indidan OLDIN); `opacity` — canvas qatlami CSS shaffofligi (yig'indidan KEYIN, maksimumni cheklaydi). Avval `opacity`ni buring — §11 |
| Halo masshtabi | `haloK = clamp(shapeS/880, 0.7, 1)` — `resize()`; kichik chizmada (mobil) halolar qalashmasin |
| Kross chegarasi | `if (p.r > 2.9 \|\| glint > 0.45)` — 2.9 = faqat 4% boost olgan yulduz (boost'siz maksimum r = 2.9) |
| O'qilishni o'lchash | `node tools/sf-measure.mjs <url> <outDir> <tag> [w] [h]` — matn ostidagi canvas yorug'ligi, 9 scroll-nuqta, skrinshotlar |
| Morph tezligi | `sp.cur += (…) × 0.065` va prujina `× 0.085` |
| Yoy kuchi | `arc = sin(e·π) × (h1−0.5) × 0.22` |
| Shakl o'lchami/joyi | `proj()` — `s ≤ 880px`, markaz `x: 60% (desktop)`, `y: 52%` |
| Ranglar | `sprites` / `coreCols` / `strokeCols` massivlari |
| Chiziq zichligi | `anchorStep`, `dmax = 5vmin`, alpha `0.24` |
| Yangi obida qo'shish | yangi `drawX(g)` funksiya yozing → `SHAPES` massiviga `sampleShape(drawX, N)` qo'shing → `SF_NAMES` ga nom qo'shing |

## 8. Production saytga (Django/HTMX) ko'chirish

Komponent React'ga deyarli bog'liq emas — faqat mount/unmount uchun ishlatiladi. Ko'chirish:

1. `starfield.jsx` ichidagi IIFE mantiqini oddiy `starfield.js` ga oling.
2. `KhivaStarfield` o'rniga: `const canvas = document.createElement('canvas')` yaratib
   `document.body.prepend(canvas)` qiling, useEffect tanasini `init()` funksiyaga o'rang.
3. React holatlari yo'q — `intensity`/`lines` ni oddiy konfiguratsiya obyektidan o'qing.
4. Sahifa kontenti `position: relative; z-index: 1` o'ramda bo'lishi shart.

---

## 9. Production holati (2026-06-10)

§8 bo'yicha ko'chirildi:

- Kod: `backend/static/js/starfield.js` — vanilla IIFE, `init()` canvas'ni
  `document.body.prepend()` qiladi (fixed, `z-index: 0`, `pointer-events: none`).
- Konfiguratsiya: `window.XIVA_STARFIELD = { intensity: 0..1, lines: bool, opacity: 0..1 }`
  (ixtiyoriy; `intensity`/`lines` har kadrda o'qiladi, default `1`/`true`;
  `opacity` init'da o'qiladi → canvas CSS shaffofligi, default 1 — §11).
- Ulanish: faqat bosh sahifa — `home.html` `extra_js` blokida `<script>`;
  kontent `.sf-wrap` (`position: relative; z-index: 1`) o'ramida.
- Shaffof seksiyalar: `site.css` dagi `.ticker-band--sf`, `.band--sf`,
  `.surface-raised--sf` modifikatorlari (§5 dagi qiymatlar bilan).

## 10. 2026-07-12 reviziyasi (portret + yomg'ir + xiralik)

- **Yakuniy shakl (index 4)** endi galaktika emas — **KHAN 天 logotipi**
  (egasining kanal-brendi). Manba: `static/images/sf-portrait.png` —
  kanal avataridan PIL threshold (lum > 110) bilan olingan oq-nuqtali PNG.
  PNG async yuklanadi; yuklanguncha galaktika fallback. (Avval yuz-portret
  sinab ko'rilgan edi — egasi logotipni tanladi, 2026-07-12.)
- **Yorug'lik**: `home.html` da `window.XIVA_STARFIELD = { intensity: 0.7 }` —
  yulduzlar matn bilan aralashmasligi uchun -30%. **Yetarli bo'lmadi** — mehmonlar
  matnni o'qiy olmadi; sabab va yechim §11 da.
- **Uchar yulduzlar**: bitta meteor → **pool (5 tagacha parallel)**, spawn
  intervali 4.5–10.5s → 0.9–2.5s (~4-5x ko'p). `METEOR_MAX` bilan sozlanadi.

## 11. 2026-09-05 reviziyasi (o'qilish: yulduzlar matnni yutmasin)

Egasi: «yulduzlar juda yorug', odamlar yozuvlarni o'qishga qiynalyapti». O'lchov
(`tools/sf-measure.mjs`, 1440×900 va 390×844, 9 scroll-nuqta) buni tasdiqladi: matn
ostidagi canvas piksellari ko'p joyda **255 (to'liq oq)** ga yetardi, mobil h1 ostida
yorug' piksellar 16%, manifest paragraflari ostida 26%.

**Sabab — additiv («lighter») qalashuv, yorug'lik knobi emas.** Band bo'ylab yulduzlar
~4px oraliqda, har biri 12.5px halo + (39% yulduzda!) 16–40px diffraksiya krossi chizardi.
3–5 halo bir pikselda yig'ilib oq «arqon» bo'lardi. `intensity` har yulduz alfasini
chiziqli kamaytiradi — yig'indi hali ham 1.0 dan oshib clip bo'laveradi; shu sabab
2026-07-12 dagi 1.0 → 0.7 sezilmadi.

**Yechim (uch qatlam):**

| Nima | Oldin | Keyin | Nega |
|---|---|---|---|
| `opacity` (yangi knob, `home.html`) | — | **0.6** | canvas CSS shaffofligi — yig'indidan KEYIN; maksimum 255 → 153, hech qaysi turkum oq bo'lolmaydi |
| Halo alpha / o'lcham | `a·0.85`, `r·(6.4+glint·6.5)` | `a·0.5`, `r·(5.0+glint·5.5)·haloK` | qalashuvning asosiy manbai |
| Kross chegarasi / alpha | `r > 2.2` (39% yulduz), `a·0.55` | `r > 2.9` (4% yirik), `a·0.35` | dizayn niyati «yirik yoki chaqnayotgan» edi |
| Glint amplitudasi | `+glint·0.7` | `+glint·0.45` | chaqnash to'liq oqqa yetmasin |
| Streak alpha | `a·0.9` | `a·0.6` | morph paytidagi «bulut» |
| Mobil N / halo | 820, halo px-da bir xil | **560**, `haloK = clamp(shapeS/880, 0.7, 1)` | 366px chizmada bir xil px-halo 2.4× kattaroq nisbiy iz qoldirardi |
| `intensity` | 0.7 | 0.7 (o'zgarmadi) | yadro/rang/iplar/meteorlar o'z kuchini saqlasin |

**Natija (matn ostidagi canvas, o'rtacha barcha ko'rinadigan matn elementlari bo'yicha):**

| Ko'rsatkich | Desktop oldin → keyin | Mobil oldin → keyin |
|---|---|---|
| yorug' piksellar (L>60) | 3.54% → 0.97% | 6.48% → 1.04% |
| «issiq» piksellar (L>140) | 1.36% → 0.28% | 3.27% → 0.32% |
| >5% yorug' elementlar | 26 → 3 | 18 → 4 |
| o'rtacha yorug'lik (0..255) | 6.6 → 2.0 | 11.9 → 1.8 |
| maksimum | 255 → 153 | 255 → 153 |

Tekshirish: `node --check backend/static/js/starfield.js` · perl curly-quote skan (faqat
`SF_NAMES` dagi 3 ta oldingi apostrof chiqishi kerak) · `RM=1` bilan reduced-motion o'tishi.

**Hali ham yorug' desa** — birinchi `opacity`ni 0.6 → 0.5 ga buring (bir raqam, `home.html`).
Zaxira levers (qo'llanmagan): hero ostida token-derivativ matn-skrimi
(`.sf-wrap .hero::before`, `color-mix(in oklab, var(--bg-0) 45%, transparent)` gradienti,
≤1024px da tekis); shaffof `.section` bloklariga `.section--sf` pardasi; `proj()` markazini
60% → 72% ga surish (barcha 5 shakl siljiydi — ehtiyot).
