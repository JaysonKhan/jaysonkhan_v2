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

- Soni: **1800** (desktop) / **820** (mobil, `<768px`).
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
| Yulduz halosi | 64px radial-gradient sprite, `globalCompositeOperation: "lighter"` (additiv nur) |
| O'tkir yadro | `arc()` to'liq alpha bilan — yulduz tiniq ko'rinadi |
| Diffraksiya nurlari | `r > 2.2` yoki chaqnash paytida 4 tomonlama ingichka kross |
| Chaqnash (glint) | `sin^28` puls — yulduz vaqti-vaqti bilan yarqiraydi |
| Harakat izi (streak) | tezlik > 1.6px bo'lsa orqaga 3.4× chiziq — "oqib o'tish" effekti |
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
| Zarra soni | `const N = mobile ? 820 : 1800` |
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
- Konfiguratsiya: `window.XIVA_STARFIELD = { intensity: 0..1, lines: bool }`
  (ixtiyoriy, har kadrda o'qiladi; default `intensity: 1`, `lines: true`).
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
  yulduzlar matn bilan aralashmasligi uchun -30%.
- **Uchar yulduzlar**: bitta meteor → **pool (5 tagacha parallel)**, spawn
  intervali 4.5–10.5s → 0.9–2.5s (~4-5x ko'p). `METEOR_MAX` bilan sozlanadi.
