# SITE-OPERATIONS.md — jaysonkhan.com yuritish qo'llanmasi

> Egasi uchun kundalik amaliy qo'llanma: kontent qayerdan keladi, qanday
> o'zgartiriladi, qanday deploy qilinadi, nimani kuzatish kerak.
> Texnik invariantlar: [`../CLAUDE.md`](../CLAUDE.md) · UI qonuni: [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md)

---

## 1. Kontent qatlamlari — nima qayerdan keladi

Saytdagi har bir matn 4 qatlamning BITTASIDAN keladi. O'zgartirishdan oldin
qaysi qatlamga tegishli ekanini aniqlang — aks holda o'zgarish yo ko'rinmaydi,
yo keyingi deploy'da o'chib ketadi:

| Qatlam | Nima kiradi | Qayerda | Qanday o'zgartiriladi |
|---|---|---|---|
| **1. Seeder-owned** (har deploy'da qayta yoziladi!) | Hero, About, FAQ, statistika (4 ta raqam+label), sayt title/meta, footer, sahifa sarlavhalari, CTA/kontakt holati; UzExam/EduStats loyiha kartalari; Experience matnlari | `backend/apps/ops/management/commands/apply_edtech_founder_copy.py` va `apply_edtech_projects.py` | Seeder faylini tahrirlash → commit → `./deploy.sh`. **Admin'dan o'zgartirmang** — keyingi deploy'da seeder ustidan yozadi |
| **2. Admin-owned** (DB, seeder tegmaydi) | Blog postlar, boshqa Project'lar (tez-chakana...), Experience sana/kompaniya, Skill'lar, TeamMember, editorial JSON bo'limlar (manifesto, process, ticker, team values) | Admin panel (`ADMIN_URL` env'dagi slug) | Admin orqali bemalol |
| **3. Template `{% trans %}` satrlari** | Tugma/label'lar: "Start a project", "View all projects", "PRESENT"... | `backend/locale/{xo,uz,ru,en}/LC_MESSAGES/django.po` | `.po` tahrir → `manage.py compilemessages -l xo` (lokalda!) → **`.mo` ham commit** → deploy. deploy.sh compilemessages QILMAYDI |
| **4. Bir martalik seed** | XIVA v4 dizayn copy (bir marta yozilgan) | `apply_xiva_copy.py` (deploy'da ISHLAMAYDI) | Endi bu maydonlarning bir qismi founder-seeder'ga ko'chgan; qolganlari admin-owned |

**Oltin qoida:** seeder-owned maydonni o'zgartirish = seeder kodini o'zgartirish.
Data migration YOZMANG (seeder baribir ustidan yozadi), admin'da ham o'zgartirmang.

## 2. Statistika bo'limi (Numbers band) — 2026-07-10 saboq

Bosh sahifadagi 4 raqam `SiteSettings.stat_{1..4}_{count,suffix,label}` dan keladi:

- `count`+`suffix` — PLAIN (tilga bog'liq emas), `label` — 4 tilda tarjima qilinadigan maydon.
- Ikkalasi ham `apply_edtech_founder_copy.py` da: count/suffix `PLAIN` dict'da,
  label'lar `COPY["stat_N_label"]` da. **Raqamni o'zgartirsangiz — label'ni ham birga tekshiring.**
- 2026-06 xato: seeder faqat count'larni yangilagan, label'lar eski mobil-davr
  matnida qolgan → "40k+ Years experience" bo'lib chiqqan. Hozirgi to'g'ri juftliklar:
  `3+ yil tajriba · 25+ ilova · 60k+ savol (UzExam) · 55k+ foydalanuvchi (52k EduStats + 5.2k UzExam)`.
- Raqamlar o'sganda (savollar bazasi, foydalanuvchilar) — seeder'dagi qiymatni
  yangilang va deploy qiling. Manba raqamlar: UzExam/EduStats admin panellari.

## 3. xo (Xorazm shevasi) — uslub qonuni

`xo` — saytning DEFAULT tili va egasining imzo-ovozi. Mashina tarjimasi TAQIQLANADI.
Yangi xo matn yozishda kanal (@jayson_khan) uslubiga tayaniladi:

| Adabiy | xo (sheva) | Misol |
|---|---|---|
| men / mening / meni | **man / mani** | "Man Jayson Khan", "mani loyihalarim" |
| -lar (ko'plik) | **-la** | ilovala, platformala, savolla, foydalanuvchila, yozuvla |
| kel / kirish | **gal / girish** | "Gal, ishlashamiz", "Girish" (login) |
| yoki | **yo** | "test platforma yo AI mentor" |
| qanday / qalay | **qale** | "qale eplaydi?", "qale bog'lansa bo'ladi?" |
| ko'ringlar / qaranglar (buyruq ko'pl.) | **-ila / -avering** | "Ishlani ko'rila", "yozavering" |
| shu yerda | **shetta** | (juda norasmiy — faqat blog/kanalda) |

Qoidalar:
1. uz/ru/en — adabiy til; sheva FAQAT xo ustunlarida (`*_xo` maydonlar, `locale/xo/`).
2. Professional kontekst (hero, about, FAQ) — sheva "yengil doza": man/mani + -la + yo.
   Kuchli sheva ("qivomman", "shetta", "keragooov") — faqat blog/norasmiy matnlarda.
3. Rasmiy atamalar (AI EdTech, Clean Architecture, production) — o'zgarmaydi.
4. Shubhalansangiz — kanaldagi real postlardan qidiring; u yerda yo'q shaklni ishlatmang.

## 4. Deploy oqimi (NON-NEGOTIABLE)

```bash
# 1. Lokal tahrir + tekshiruv
cd backend
./venv/bin/python manage.py check
./venv/bin/python manage.py test --settings=config.settings.dev   # 34+ test, hammasi yashil
# kontent o'zgargan bo'lsa — lokal render-test:
./venv/bin/python manage.py apply_edtech_founder_copy && ./venv/bin/python manage.py apply_edtech_projects

# 2. Commit + deploy (serverda HECH QACHON fayl tahrirlanmaydi)
git add -A && git commit -m "..."
./deploy.sh "commit message"
# deploy o'zi: push → server pull → pip → migrate → collectstatic →
# ikkala seeder → restart jaysonkhan + nginx reload → bot komandalar → cron blok → health check

# 3. Tasdiqlash
git rev-parse --short HEAD          # == origin/main bo'lishi kerak
curl -s -o /dev/null -w '%{http_code}' https://jaysonkhan.com/xo/   # 200
```

- SiteSettings 5 daqiqa kesh'lanadi. Seeder `obj.save()` chaqirgani uchun kesh
  o'z-o'zidan yangilanadi. Agar kontent data-MIGRATION orqali kirgan bo'lsa
  (post_save otilmaydi) — serverda qo'lda bust:
  `manage.py shell -c "from django.apps import apps; S=apps.get_model('core','SiteSettings'); S.objects.get(pk=1).save()"`
- `robots.txt`/`humans.txt`/`llms.txt` `cache_page` bilan Redis'da — ularni
  o'zgartirsangiz Redis'ni tozalang (restart yetarli emas).

## 5. Loyihalar (Projects) boshqaruvi

- **uzexam, edustats** — seeder-owned (`apply_edtech_projects.py`): karta matni,
  chip'lar (`stats` JSON), tartib, ko'rinish. Faktlarni yangilash = seeder tahriri.
- **talabaovozi** — legacy karta, EduStats ichiga birlashtirilgan (2026-07-10):
  seeder uni har deploy'da `is_visible=False` qiladi. Qayta ko'rsatish kerak bo'lsa —
  seeder'dagi `HIDE_SLUGS` dan olib tashlang.
- **Boshqalari** (tez-chakana va h.k.) — admin-owned: `is_visible`, `is_featured`,
  `order` bayroqlari bilan boshqariladi.
- Karta chip'lari (`Project.stats`) tilga bog'lanmagan JSON:
  `[{"v": "60k+", "l": "questions"}, ...]` — qisqa, lotincha yozing.

## 6. Experience (Career timeline)

- Qatorlar (kompaniya, sanalar, tartib) — admin-owned; seeder qator YARATMAYDI.
- Lavozim + tavsif MATNLARI — seeder-owned (`EXPERIENCE` ro'yxati,
  `company__icontains` bo'yicha topadi). Yangi ish joyi qo'shilsa: avval admin'da
  qator yarating, keyin xohlasangiz seeder'ga matnini qo'shing.

## 7. Monitoring va loglar

**Telegram bot (owner-only):** `/start /notifications /status /services /disk /tariff /logs [service] [lines] /backup`

**Cron'lar (5 ta, hammasi `manage.py cron_run <target>` orqali, tarixi `ops.CronRun` da):**
check_cpu_alert · service_health_check · cron_health_check · server_health_report · monthly_log_report.
Crontab — `security/install-servermonitor-cron.sh` o'rnatadigan marker-blok; qo'lda qator QO'SHMANG.

**Loglarni ko'rish:**
```bash
ssh jaysonkhan "sudo journalctl -u jaysonkhan -n 100 --no-pager"      # Django/Gunicorn
ssh jaysonkhan "sudo tail -50 /var/log/nginx/error.log"               # Nginx
# yoki Telegram botdan: /logs jaysonkhan 50
```

**Yolg'on signallar** (tuzatishga urinmang): ~13 soniyalik davriy 500 burst =
unattended-upgrades postgresql restart — o'zi tiklanadi.

## 8. WakaTime widget

Bosh sahifa About yonidagi grafik `SiteSettings.wakatime_stats` JSON'idan.
Cron `manage.py fetch_wakatime` to'ldiradi (`WAKATIME_API_KEY` env). Bo'sh dict →
widget yashirinadi, `about_image` chiqadi.

## 9. Tez-tez uchraydigan holatlar (runbook)

| Simptom | Sabab | Yechim |
|---|---|---|
| Admin'da o'zgartirdim, deploy'dan keyin eskisi qaytdi | Maydon seeder-owned | O'zgarishni seeder'ga ko'chiring (§1 jadval) |
| Kontent o'zgardi lekin saytda eski | SiteSettings kesh (5 daq) | Kuting yoki qo'lda bust (§4) |
| xo sahifada uz matn chiqyapti | `*_xo` ustun bo'sh → fallback | Seeder/admin'da xo qiymatni to'ldiring |
| .po tahriri saytda ko'rinmayapti | `.mo` kompilyatsiya/commit qilinmagan | `compilemessages -l xo` + `.mo` commit + deploy |
| Statistika raqam/label mos emas | Seeder'da faqat bittasi yangilangan | §2 — count va label birga yangilanadi |
| Sahifa ochilmayapti, `check` yashil | Inline JS'da curly quote yo template comment leak | CLAUDE.md gotcha #10/#11 |

---

*Yaratilgan: 2026-07-10. Kontent-fakt manbalari: resume (2026-07), UzExam PTA-2026
hujjatlari, EduStats rate card. Yangi katta fakt (foydalanuvchi soni, mukofot va h.k.)
paydo bo'lsa — seeder raqamlarini yangilang va bu faylning §2 jadvalini ham yangilang.*

## 10. Orbit seksiyasi (kontakt sahifasi, 2026-07-12)

Kontakt sahifasi pastida "quyosh sistemasi": markazda egasining rasmi
(`static/images/jayson-orbit.jpg`), atrofida saytga Telegram orqali kirgan
mehmonlar (TelegramEntity, `sources__service='site'`) aylanadi — eng so'nggi
12 rasmli = sayyora, keyingi 6 = mini-yo'ldosh. Mantiq: `ContactView.get_context_data`
(presentation/web/views.py) + `static/js/orbit.js` + `site.css` `.orbit-*` bloklari.
Mehmon ko'paygani sari ro'yxat o'zi yangilanadi; hech narsa sozlash shart emas.
Egasining markaziy rasmini almashtirish = `jayson-orbit.jpg` faylini yangilash
(+ xohlasangiz `sf-portrait.png` yulduz-portretini ham qayta generatsiya qiling,
qarang: docs/starfield-implementation.md §10).

## 11. Gallery Wall (bosh sahifa, footer tepasida — 2026-07-17)

Gorizontal justified rasm devori: `portfolio.GalleryImage` (admin-owned!).
Rasm qo'shish: **admin → Gallery images → yangi yozuv** — rasm yuklang, 4 tilda
hint yozing (hover'da chiqadi), order bering. O'lchamlar avtomatik saqlanadi
(layout sakramasligi uchun `--ar` serverdan keladi). 20 tadan sahifalanadi:
birinchisi server-render, qolgani "Yana ko'rila" bilan silliq qo'shiladi
(`gallery/feed/` JSON — til-prefiksli, gotcha #12). Media serverda:
`/var/www/jaysonkhan/media/gallery/`. Kod: `presentation/web/views.py`
(GalleryFeedView), `static/js/gallery-wall.js`, `site.css` `.gw-*` bloklari.

## 12. Anime cover + lightbox (2026-07-17)

**Ikki rasm tizimi.** Har `GalleryImage`da 2 ta rasm bor:
- `image` — ASOSIY (real) rasm, lightbox'da bosilganda ochiladi.
- `cover` — devorda KO'RINADIGAN anime/ghibli versiya (bo'sh bo'lsa `image` ko'rinadi).

Devorda cover, bosilganda `image` — FLIP "hero" animatsiyasi bilan (cover markazga
uchadi, keyin real rasmga crossfade). Kod: `static/js/lightbox.js` +
`site.css` `.lb-*` bloklari. Trigger: `[data-lightbox]` (gallery figure + about).

**About rasm** ham xuddi shunday: `SiteSettings.about_image` (real) +
`about_image_anime` (ko'rinadigan anime cover). Admin → Sayt sozlamalari →
Homepage tab → About bo'limi'da ikkalasini yuklaysiz.

**Yangi anime cover yasash** (Higgsfield `nano_banana_pro` bilan ishlagan):
prompt = "Transform this photograph into a hand-painted Studio Ghibli /
Makoto Shinkai anime illustration... Preserve the EXACT same composition...
only convert the rendering style to anime." Kuchli "UNMISTAKABLY 2D anime cel"
urg'usi shart — aks holda realistik chiqadi. Jurnal-layout (about) uchun barcha
matnni "keep EXACT typography, only the person becomes anime" deb saqlab qoldiring.
Cover fayllari serverda: `/var/www/jaysonkhan/media/gallery/covers/` va
`/var/www/jaysonkhan/media/about/`.
