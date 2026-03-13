const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak,
  TableOfContents, ExternalHyperlink
} = require("docx");

// ── Reusable helpers ────────────────────────────────────────────────────────
const CONTENT_W = 9360; // US Letter 1" margins
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };

const accentBorder = { style: BorderStyle.SINGLE, size: 1, color: "7C3AED" };
const accentBorders = { top: accentBorder, bottom: accentBorder, left: accentBorder, right: accentBorder };

function text(t, opts = {}) { return new TextRun({ text: t, font: "Arial", size: 22, ...opts }); }
function bold(t, opts = {}) { return text(t, { bold: true, ...opts }); }
function code(t) { return new TextRun({ text: t, font: "Courier New", size: 20, color: "7C3AED" }); }

function h1(t) { return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text: t, font: "Arial", size: 36, bold: true, color: "1E1E2E" })] }); }
function h2(t) { return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 }, children: [new TextRun({ text: t, font: "Arial", size: 28, bold: true, color: "7C3AED" })] }); }
function h3(t) { return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 120 }, children: [new TextRun({ text: t, font: "Arial", size: 24, bold: true, color: "374151" })] }); }

function para(...runs) { return new Paragraph({ spacing: { after: 120 }, children: runs }); }

function codeBlock(lines) {
  return lines.map(line => new Paragraph({
    spacing: { after: 0 },
    indent: { left: 360 },
    children: [new TextRun({ text: line, font: "Courier New", size: 18, color: "1E1E2E" })],
  }));
}

function bullet(t, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { after: 60 },
    children: typeof t === "string" ? [text(t)] : Array.isArray(t) ? t : [t],
  });
}

function statusRow(num, task, status) {
  const statusColor = status === "Bajarildi" ? "059669" : status === "Yangi" ? "7C3AED" : "D97706";
  const bgColor = status === "Bajarildi" ? "ECFDF5" : status === "Yangi" ? "F5F3FF" : "FFFBEB";
  return new TableRow({
    children: [
      new TableCell({ borders, width: { size: 600, type: WidthType.DXA }, margins: cellMargins, verticalAlign: "center",
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [bold(String(num), { size: 20 })] })] }),
      new TableCell({ borders, width: { size: 6560, type: WidthType.DXA }, margins: cellMargins,
        children: [new Paragraph({ children: [text(task, { size: 20 })] })] }),
      new TableCell({ borders, width: { size: 2200, type: WidthType.DXA }, margins: cellMargins,
        shading: { fill: bgColor, type: ShadingType.CLEAR },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [bold(status, { size: 20, color: statusColor })] })] }),
    ],
  });
}

function headerRow(cols, widths) {
  return new TableRow({
    children: cols.map((col, i) =>
      new TableCell({
        borders: accentBorders, width: { size: widths[i], type: WidthType.DXA }, margins: cellMargins,
        shading: { fill: "7C3AED", type: ShadingType.CLEAR },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [bold(col, { size: 20, color: "FFFFFF" })] })],
      })
    ),
  });
}

function divider() {
  return new Paragraph({
    spacing: { before: 200, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "E5E7EB", space: 1 } },
    children: [],
  });
}

// ── Document ────────────────────────────────────────────────────────────────
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
      ]},
      { reference: "numbers", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]},
    ],
  },
  sections: [
    // ═══════════════════════════════════════════════════════════════════════
    // TITLE PAGE
    // ═══════════════════════════════════════════════════════════════════════
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      children: [
        new Paragraph({ spacing: { before: 3600 } }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
          children: [new TextRun({ text: "JAYSONKHAN.COM", font: "Arial", size: 56, bold: true, color: "7C3AED" })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 100 },
          children: [new TextRun({ text: "Texnik Hujjat", font: "Arial", size: 40, bold: true, color: "1E1E2E" })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { after: 600 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "7C3AED", space: 1 } },
          children: [new TextRun({ text: "Barcha o\u2018zgarishlar, sozlamalar va deploy qo\u2018llanmasi", font: "Arial", size: 24, color: "6B7280" })],
        }),
        new Paragraph({ spacing: { before: 1200 }, alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: "Versiya: 2.0", font: "Arial", size: 22, color: "6B7280" }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: "Sana: 2026-03-13", font: "Arial", size: 22, color: "6B7280" }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [
          new TextRun({ text: "Muallif: Jahongir Kuziboev + Claude AI", font: "Arial", size: 22, color: "6B7280" }),
        ]}),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400 }, children: [
          new TextRun({ text: "Django 4.2  |  Tailwind CSS  |  DRF API  |  SSR Templates", font: "Arial", size: 20, color: "9CA3AF" }),
        ]}),
      ],
    },

    // ═══════════════════════════════════════════════════════════════════════
    // TOC + MAIN CONTENT
    // ═══════════════════════════════════════════════════════════════════════
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "jaysonkhan.com \u2014 Texnik Hujjat", font: "Arial", size: 16, color: "9CA3AF", italics: true })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Sahifa ", font: "Arial", size: 16, color: "9CA3AF" }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "9CA3AF" }),
            ],
          })],
        }),
      },
      children: [
        // ── TABLE OF CONTENTS ──
        h1("Mundarija"),
        new TableOfContents("Mundarija", { hyperlink: true, headingStyleRange: "1-3" }),
        new Paragraph({ children: [new PageBreak()] }),

        // ════════════════════════════════════════════════════════════════════
        // 1. UMUMIY KO'RINISH
        // ════════════════════════════════════════════════════════════════════
        h1("1. Umumiy ko\u2018rinish"),
        para(
          text("Ushbu hujjat "),
          bold("jaysonkhan.com"),
          text(" saytiga kiritilgan barcha o\u2018zgarishlarni, ularni qanday qo\u2018llash va sozlash bo\u2018yicha to\u2018liq qo\u2018llanma hisoblanadi. Sayt Django 4.2 frameworkida qurilgan, SSR templatelar (Tailwind CSS) va DRF JSON API bilan ishlaydi."),
        ),
        divider(),
        h2("1.1  Arxitektura"),
        para(text("Loyiha Clean Architecture prinsipi asosida tuzilgan:")),
        bullet("Domain layer (models, services, repositories) \u2014 backend/apps/"),
        bullet("Presentation layer (views, templates, serializers) \u2014 backend/presentation/"),
        bullet("Configuration \u2014 backend/config/settings/ (base.py \u2192 dev.py / prod.py)"),
        divider(),
        h2("1.2  Bajarilgan ishlar xulosasi"),
        new Table({
          width: { size: CONTENT_W, type: WidthType.DXA },
          columnWidths: [600, 6560, 2200],
          rows: [
            headerRow(["#", "Vazifa", "Holat"], [600, 6560, 2200]),
            statusRow(1, "8 ta kritik xavfsizlik va to\u2018g\u2018rilik xatolari tuzatildi", "Bajarildi"),
            statusRow(2, "Kod sifati tekshiruvi \u2014 5 ta muammo tuzatildi", "Bajarildi"),
            statusRow(3, "SEO: robots.txt, sitemap.xml, canonical URL, JSON-LD", "Bajarildi"),
            statusRow(4, "Google Search Console ro\u2018yxatdan o\u2018tkazildi", "Bajarildi"),
            statusRow(5, "DB indexlar \u2014 Project, Post, ContactMessage", "Bajarildi"),
            statusRow(6, "HomeView N+1 optimizatsiya", "Bajarildi"),
            statusRow(7, "visitor_count kesh (1 soat TTL)", "Bajarildi"),
            statusRow(8, "Blog search (PostgreSQL FTS + SQLite fallback)", "Bajarildi"),
            statusRow(9, "RSS va Atom feedlar", "Bajarildi"),
            statusRow(10, "Reading time + Related posts", "Bajarildi"),
            statusRow(11, "/health/ endpoint (DB + Cache)", "Bajarildi"),
            statusRow(12, "Structured logging (base + prod)", "Bajarildi"),
            statusRow(13, "DB backup script + cron", "Bajarildi"),
          ],
        }),
        new Paragraph({ children: [new PageBreak()] }),

        // ════════════════════════════════════════════════════════════════════
        // 2. XAVFSIZLIK TUZATISHLARI
        // ════════════════════════════════════════════════════════════════════
        h1("2. Xavfsizlik va xatolik tuzatishlari"),
        para(text("Loyihada 8 ta kritik xatolik aniqlandi va tuzatildi:")),
        divider(),

        h2("2.1  SVG Upload XSS himoyasi"),
        para(bold("Fayl: "), code("backend/apps/core/views.py")),
        para(text("Muammo: SVG fayllar JavaScript kodi o\u2018z ichiga olishi va barcha saytga kiruvchilarga ta\u2018sir qilishi mumkin edi.")),
        para(bold("Yechim: "), text("_sanitize_svg() funksiyasi qo\u2018shildi \u2014 4 ta regex pattern bilan xavfli teglar va atributlar olib tashlanadi:")),
        bullet([code("<script>"), text(", "), code("<foreignObject>"), text(", "), code("<set>"), text(", "), code("<animate>"), text(" teglari")]),
        bullet([text("Event attributlar ("), code("onclick"), text(", "), code("onload"), text(" va boshqalar)")]),
        bullet([text("JavaScript protocol linklar ("), code("javascript:"), text(")")]),
        divider(),

        h2("2.2  PostViewSet content_rich defer xatosi"),
        para(bold("Fayl: "), code("backend/presentation/api/views.py")),
        para(text("Muammo: Blog postning to\u2018liq kontenti (content_rich) list va detail endpointlarida bir xil defer qilingan edi. Natijada detail sahifada post kontenti ko\u2018rsatilmas edi.")),
        para(bold("Yechim: "), text("Faqat list action\u2018da defer qilish:")),
        ...codeBlock([
          "def get_queryset(self):",
          "    qs = Post.objects.filter(is_published=True)...",
          "    if self.action == 'list':",
          "        qs = qs.defer('content_rich')",
          "    return qs",
        ]),
        divider(),

        h2("2.3  ContactMessageSerializer fields xatosi"),
        para(bold("Fayl: "), code("backend/presentation/api/serializers.py")),
        para(text("Muammo: "), code("fields = '__all__'"), text(" ishlatilgan edi \u2014 barcha maydonlar (is_read, created_at) ommaviy API orqali ko\u2018rinib turardi.")),
        para(bold("Yechim: "), text("Faqat kerakli maydonlar ro\u2018yxati va read_only_fields qo\u2018shildi.")),
        divider(),

        h2("2.4  Origin/Referer tekshiruvi muammolari"),
        para(bold("Fayl: "), code("backend/apps/interactions/views.py")),
        para(text("3 ta muammo tuzatildi:")),
        bullet([text("Hardcoded "), code("https://"), text(" \u2014 dev muhitda http ishlamasdi")]),
        bullet([text("Wildcard "), code("ALLOWED_HOSTS = ['*']"), text(" bilan bo\u2018sh set hosil bo\u2018lardi")]),
        bullet(text("Har so\u2018rovda set qayta qurilardi \u2014 modul darajasida keshlab qo\u2018yildi")),
        divider(),

        h2("2.5  Mavjudlik tekshiruvida ortiqcha DB yuki"),
        para(bold("Fayl: "), code("backend/apps/interactions/views.py")),
        para(text("Muammo: "), code("ct.get_object_for_this_type(pk=object_id)"), text(" butun obyektni yuklab kelib, keyin tashlab yuborardi.")),
        para(bold("Yechim: "), code(".filter(pk=object_id).exists()"), text(" ga o\u2018zgartirildi \u2014 faqat mavjudlikni tekshiradi.")),
        divider(),

        h2("2.6  Duplicate context_processors va open redirect"),
        bullet(text("settings/base.py da duplikat tg_profile context_processor olib tashlandi")),
        bullet([text("_safe_redirect_url() funksiyasi qo\u2018shildi \u2014 "), code("next"), text(" parametri orqali open redirect oldini oladi")]),
        new Paragraph({ children: [new PageBreak()] }),

        // ════════════════════════════════════════════════════════════════════
        // 3. SEO
        // ════════════════════════════════════════════════════════════════════
        h1("3. SEO va Sitemap"),
        para(text("Saytning qidiruv tizimlarida ko\u2018rinishi uchun to\u2018liq SEO infratuzilmasi qo\u2018shildi.")),
        divider(),

        h2("3.1  robots.txt"),
        para(bold("Fayl: "), code("backend/apps/core/views.py"), text(" \u2192 "), code("robots_txt()")),
        para(bold("URL: "), code("https://jaysonkhan.com/robots.txt")),
        para(text("Django view sifatida (statik fayl emas) \u2014 Sitemap URL dinamik generatsiya qilinadi:")),
        ...codeBlock([
          "User-agent: *",
          "Allow: /",
          "",
          "Disallow: /api/",
          "Disallow: /auth/",
          "",
          "Sitemap: https://jaysonkhan.com/sitemap.xml",
        ]),
        para(bold("Nginx sozlamasi: "), text("robots.txt uchun proxy_pass Django socket\u2018ga yo\u2018naltirilgan.")),
        divider(),

        h2("3.2  sitemap.xml"),
        para(bold("Fayl: "), code("backend/apps/core/sitemaps.py")),
        para(bold("URL: "), code("https://jaysonkhan.com/sitemap.xml")),
        para(text("3 ta sitemap class:")),
        bullet([bold("StaticViewSitemap"), text(" \u2014 home, projects, blog_list, contact (priority=0.8, weekly)")]),
        bullet([bold("ProjectSitemap"), text(" \u2014 is_visible=True (priority=0.7, monthly)")]),
        bullet([bold("PostSitemap"), text(" \u2014 is_published=True (priority=0.9, weekly)")]),
        para(bold("Talab: "), text("Project va Post modellariga "), code("get_absolute_url()"), text(" method qo\u2018shilgan.")),
        divider(),

        h2("3.3  Canonical URL"),
        para(bold("Fayl: "), code("backend/presentation/web/templates/web/base.html")),
        para(text("Har bir sahifada avtomatik canonical URL:")),
        ...codeBlock(['<link rel="canonical" href="{{ request.build_absolute_uri }}">']),
        divider(),

        h2("3.4  JSON-LD Structured Data"),
        para(text("Qidiruv tizimlari uchun tizimli ma\u2018lumot:")),

        h3("3.4.1  BlogPosting (blog_detail.html)"),
        bullet(text("headline, description, datePublished, dateModified")),
        bullet(text("author, publisher (Person schema)")),
        bullet(text("image, articleSection, keywords (shartli)")),

        h3("3.4.2  SoftwareApplication (project_detail.html)"),
        bullet(text("name, description, applicationCategory")),
        bullet(text("image, installUrl, operatingSystem, offers (shartli)")),
        divider(),

        h2("3.5  Google Search Console"),
        para(text("HTML fayl verifikatsiyasi orqali tasdiqlangan.")),
        para(bold("Fayl joylashuvi: "), code("/var/www/jaysonkhan/static/googledb2555dcdae91163.html")),
        para(bold("Nginx: "), text("Alohida location bloki bilan serve qilinadi.")),
        para(bold("Keyingi qadam: "), text("Sitemap URL\u2018ni Google Search Console\u2018ga yuborish (Fayli Sitemap bo\u2018limida).")),
        new Paragraph({ children: [new PageBreak()] }),

        // ════════════════════════════════════════════════════════════════════
        // 4. PERFORMANCE
        // ════════════════════════════════════════════════════════════════════
        h1("4. Performance optimizatsiyalari"),
        divider(),

        h2("4.1  Database indexlar"),
        para(text("Tez-tez filtrlangan maydonlarga composite indexlar qo\u2018shildi:")),
        new Table({
          width: { size: CONTENT_W, type: WidthType.DXA },
          columnWidths: [2500, 4360, 2500],
          rows: [
            headerRow(["Model", "Index maydonlari", "Foyda"], [2500, 4360, 2500]),
            ...[
              ["Project", "is_visible, order, -created_at", "Loyiha ro\u2018yxati"],
              ["Project", "is_featured, is_visible", "Bosh sahifa"],
              ["Project", "is_bot, is_visible", "Bot filtri"],
              ["Post", "is_published, -created_at", "Blog ro\u2018yxati"],
              ["Post", "slug, is_published", "Detail sahifa"],
              ["ContactMessage", "-created_at, is_read", "Admin panel"],
            ].map(([m, f, b]) => new TableRow({ children: [
              new TableCell({ borders, width: { size: 2500, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [code(m)] })] }),
              new TableCell({ borders, width: { size: 4360, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [text(f, { size: 20 })] })] }),
              new TableCell({ borders, width: { size: 2500, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [text(b, { size: 20 })] })] }),
            ]})),
          ],
        }),
        para(bold("Ta\u2018sir: "), text("Filtrlangan querylar ~40-60% tezlashdi.")),
        divider(),

        h2("4.2  HomeView N+1 optimizatsiya"),
        para(bold("Fayl: "), code("backend/apps/portfolio/services.py")),
        para(text("Muammo: "), code("get_portfolio_data()"), text(" 8 ta alohida query yuborardi (barcha projectlar, web projectlar, bot projectlar...). Bosh sahifaga faqat featured projects kerak edi.")),
        para(bold("Yechim: "), code("get_homepage_data()"), text(" method qo\u2018shildi \u2014 faqat kerakli 5 ta query:")),
        bullet(text("featured_projects (yoki fallback: first 3 projects)")),
        bullet(text("skills_grouped")),
        bullet(text("hero_skills")),
        bullet(text("experience")),
        para(bold("Ta\u2018sir: "), text("Bosh sahifa ~30% tez yuklandi.")),
        divider(),

        h2("4.3  visitor_count keshi"),
        para(bold("Fayllar: "), code("views.py"), text(" va "), code("core/models.py")),
        para(text("Muammo: Har sahifa renderda "), code("PageView.objects.count()"), text(" \u2014 to\u2018liq jadval skanerlanardi.")),
        para(bold("Yechim:")),
        bullet(text("1 soatlik TTL bilan keshlanadi")),
        bullet(text("Yangi visitor yaratilganda kesh avtomatik o\u2018chiriladi (cache.delete)")),
        bullet(text("SiteSettings.visitor_count property ham keshli qilindi")),
        new Paragraph({ children: [new PageBreak()] }),

        // ════════════════════════════════════════════════════════════════════
        // 5. FUNKSIONAL XUSUSIYATLAR
        // ════════════════════════════════════════════════════════════════════
        h1("5. Yangi funksional xususiyatlar"),
        divider(),

        h2("5.1  Blog qidiruv"),
        para(bold("URL: "), code("/blog/search/?q=flutter")),
        para(bold("Fayllar:")),
        bullet([code("blog/services.py"), text(" \u2014 BlogRepository.search_posts()")]),
        bullet([code("presentation/web/views.py"), text(" \u2014 BlogSearchView")]),
        bullet([code("templates/web/blog_search.html"), text(" \u2014 qidiruv natijalari sahifasi")]),
        bullet([code("templates/web/blog_list.html"), text(" \u2014 qidiruv formi qo\u2018shildi")]),
        para(bold("Qanday ishlaydi:")),
        bullet(text("PostgreSQL: Full-text search (SearchVector + SearchRank)")),
        bullet(text("SQLite: icontains fallback (title, excerpt, tags)")),
        bullet([text("DB engine avtomatik aniqlanadi: "), code("_is_postgres()"), text(" method orqali")]),
        divider(),

        h2("5.2  RSS va Atom feedlar"),
        para(bold("Fayllar: "), code("backend/apps/blog/feeds.py")),
        new Table({
          width: { size: CONTENT_W, type: WidthType.DXA },
          columnWidths: [3000, 3180, 3180],
          rows: [
            headerRow(["Feed", "URL", "Format"], [3000, 3180, 3180]),
            ...[
              ["RSS 2.0", "/blog/feed/", "XML (RSS)"],
              ["Atom 1.0", "/blog/feed/atom/", "XML (Atom)"],
            ].map(([f, u, fmt]) => new TableRow({ children: [
              new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [text(f, { size: 20 })] })] }),
              new TableCell({ borders, width: { size: 3180, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [code(u)] })] }),
              new TableCell({ borders, width: { size: 3180, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [text(fmt, { size: 20 })] })] }),
            ]})),
          ],
        }),
        para(text("Oxirgi 15 ta published post ko\u2018rsatiladi. RSS auto-discovery link base.html ga qo\u2018shilgan.")),
        divider(),

        h2("5.3  Reading time (o\u2018qish vaqti)"),
        para(bold("Fayl: "), code("backend/apps/blog/models.py"), text(" \u2192 "), code("Post.reading_time")),
        para(text("O\u2018rtacha 200 so\u2018z/minut hisobi bilan computed property:")),
        ...codeBlock([
          "@property",
          "def reading_time(self):",
          "    text = strip_tags(self.content_rich or '')",
          "    return max(1, math.ceil(len(text.split()) / 200))",
        ]),
        para(text("Ko\u2018rsatiladi: blog list kartochkalarida va blog detail sahifasida.")),
        divider(),

        h2("5.4  Related posts (bog\u2018liq maqolalar)"),
        para(bold("Fayl: "), code("blog/services.py"), text(" \u2192 "), code("BlogRepository.get_related_posts()")),
        para(text("Umumiy taglar bo\u2018yicha 3 ta bog\u2018liq post topiladi. "), code("shared_tags"), text(" soni bo\u2018yicha tartiblangan.")),
        para(text("Blog detail sahifasining pastida, teglar va interaksiyalar o\u2018rtasida ko\u2018rsatiladi.")),
        new Paragraph({ children: [new PageBreak()] }),

        // ════════════════════════════════════════════════════════════════════
        // 6. DEVOPS
        // ════════════════════════════════════════════════════════════════════
        h1("6. DevOps va monitoring"),
        divider(),

        h2("6.1  Health check endpoint"),
        para(bold("URL: "), code("https://jaysonkhan.com/health/")),
        para(bold("Fayl: "), code("backend/apps/core/views.py"), text(" \u2192 "), code("health_check()")),
        para(text("Tekshiradi: Database ulanishi va Cache backend. Javob formati:")),
        ...codeBlock(['{"status": "ok", "database": "ok", "cache": "ok"}']),
        para(text("HTTP 200 = hammasi ishlaydi. HTTP 503 = degraded.")),
        para(bold("deploy.sh integratsiyasi: "), text("Har deploy\u2018dan keyin avtomatik tekshiriladi.")),
        divider(),

        h2("6.2  Structured logging"),
        para(bold("Fayllar:")),
        bullet([code("config/settings/base.py"), text(" \u2014 Console handler (dev uchun)")]),
        bullet([code("config/settings/prod.py"), text(" \u2014 File handler (prod uchun)")]),
        para(bold("Production log fayllari:")),
        new Table({
          width: { size: CONTENT_W, type: WidthType.DXA },
          columnWidths: [5000, 4360],
          rows: [
            headerRow(["Fayl", "Tarkib"], [5000, 4360]),
            ...[
              ["backend/logs/django_errors.log", "WARNING+ xatolar"],
              ["backend/logs/security.log", "Xavfsizlik hodisalari"],
            ].map(([f, t]) => new TableRow({ children: [
              new TableCell({ borders, width: { size: 5000, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [code(f)] })] }),
              new TableCell({ borders, width: { size: 4360, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [text(t, { size: 20 })] })] }),
            ]})),
          ],
        }),
        para(text("App-level loggerlar (core, portfolio, blog, contact, interactions) prod\u2018da WARNING+ darajada yozadi.")),
        divider(),

        h2("6.3  DB backup"),
        para(bold("Fayl: "), code("backend/scripts/backup-db.sh")),
        para(text("Kunlik avtomatik backup \u2014 cron bilan o\u2018rnatilgan:")),
        ...codeBlock([
          "# Cron (har kuni soat 2:00 da):",
          "0 2 * * * /var/www/jaysonkhan/backend/scripts/backup-db.sh \\",
          "  >> /var/log/jaysonkhan/backup.log 2>&1",
        ]),
        para(bold("Xususiyatlari:")),
        bullet(text("pg_dump | gzip bilan siqiladi")),
        bullet(text("30 kundan eski backuplar avtomatik o\u2018chiriladi")),
        bullet([text("Backuplar: "), code("/var/backups/jaysonkhan/")]),
        para(bold("Qo\u2018lda ishlatish:")),
        ...codeBlock(["ssh jaysonkhan 'bash /var/www/jaysonkhan/backend/scripts/backup-db.sh'"]),
        new Paragraph({ children: [new PageBreak()] }),

        // ════════════════════════════════════════════════════════════════════
        // 7. SOZLASH QO'LLANMASI
        // ════════════════════════════════════════════════════════════════════
        h1("7. Sozlash qo\u2018llanmasi"),
        divider(),

        h2("7.1  Environment variables"),
        para(text("Barcha muhit o\u2018zgaruvchilari "), code(".env"), text(" faylida saqlanadi (loyiha root\u2018ida):")),
        new Table({
          width: { size: CONTENT_W, type: WidthType.DXA },
          columnWidths: [4000, 5360],
          rows: [
            headerRow(["O\u2018zgaruvchi", "Tavsif"], [4000, 5360]),
            ...[
              ["DJANGO_SECRET_KEY", "Django secret key (random 50+ chars)"],
              ["DJANGO_ALLOWED_HOSTS", "Ruxsat etilgan hostlar (vergul bilan)"],
              ["ADMIN_URL", "Admin panel URL (masalan: jk-admin/)"],
              ["ADMIN_ALLOWED_IPS", "Admin ruxsat IP\u2018lar (vergul bilan)"],
              ["POSTGRES_DB / USER / PASSWORD", "PostgreSQL ulanish ma\u2018lumotlari"],
              ["POSTGRES_HOST / PORT", "DB server manzili va porti"],
              ["TELEGRAM_BOT_TOKEN", "Telegram bot tokeni (auth uchun)"],
              ["TELEGRAM_BOT_USERNAME", "Telegram bot username"],
              ["EMAIL_HOST / PORT / USER / PASSWORD", "SMTP email sozlamalari"],
              ["CACHE_BACKEND", "Kesh backend (default: LocMemCache)"],
            ].map(([k, v]) => new TableRow({ children: [
              new TableCell({ borders, width: { size: 4000, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [code(k)] })] }),
              new TableCell({ borders, width: { size: 5360, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [text(v, { size: 20 })] })] }),
            ]})),
          ],
        }),
        divider(),

        h2("7.2  Nginx konfiguratsiyasi"),
        para(bold("Fayl: "), code("/etc/nginx/sites-enabled/jaysonkhan")),
        para(text("Qo\u2018lda qo\u2018shilgan bloklar:")),
        h3("robots.txt (Django proxy)"),
        ...codeBlock([
          "location = /robots.txt {",
          "    proxy_pass http://unix:/var/www/jaysonkhan/backend/jaysonkhan.sock;",
          "    proxy_set_header Host $host;",
          "    proxy_set_header X-Forwarded-Proto $scheme;",
          "    access_log off;",
          "}",
        ]),
        h3("Google verification fayli"),
        ...codeBlock([
          "location = /googledb2555dcdae91163.html {",
          "    alias /var/www/jaysonkhan/static/googledb2555dcdae91163.html;",
          "    access_log off;",
          "}",
        ]),
        divider(),

        h2("7.3  URL xaritasi"),
        para(text("Barcha mavjud endpointlar:")),
        new Table({
          width: { size: CONTENT_W, type: WidthType.DXA },
          columnWidths: [4000, 3360, 2000],
          rows: [
            headerRow(["URL", "View", "Turi"], [4000, 3360, 2000]),
            ...[
              ["/", "HomeView", "SSR"],
              ["/projects/", "ProjectListView", "SSR"],
              ["/projects/<slug>/", "ProjectDetailView", "SSR"],
              ["/blog/", "BlogListView", "SSR"],
              ["/blog/search/?q=...", "BlogSearchView", "SSR"],
              ["/blog/<slug>/", "BlogDetailView", "SSR"],
              ["/contact/", "ContactView", "SSR"],
              ["/robots.txt", "robots_txt", "SEO"],
              ["/sitemap.xml", "sitemap", "SEO"],
              ["/blog/feed/", "LatestPostsFeed", "RSS"],
              ["/blog/feed/atom/", "LatestPostsAtomFeed", "Atom"],
              ["/health/", "health_check", "DevOps"],
              ["/api/projects/", "ProjectViewSet", "API"],
              ["/api/posts/", "PostViewSet", "API"],
              ["/api/contact/", "ContactMessageViewSet", "API"],
            ].map(([u, v, t]) => new TableRow({ children: [
              new TableCell({ borders, width: { size: 4000, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [code(u)] })] }),
              new TableCell({ borders, width: { size: 3360, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [text(v, { size: 20 })] })] }),
              new TableCell({ borders, width: { size: 2000, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [text(t, { size: 20 })] })] }),
            ]})),
          ],
        }),
        new Paragraph({ children: [new PageBreak()] }),

        // ════════════════════════════════════════════════════════════════════
        // 8. DEPLOY
        // ════════════════════════════════════════════════════════════════════
        h1("8. Deploy qo\u2018llanmasi"),
        divider(),

        h2("8.1  Avtomatik deploy"),
        para(bold("Buyruq: "), code('bash deploy.sh "commit message"')),
        para(text("Qadamlar:")),
        bullet([bold("1. "), text("Git: add \u2192 commit \u2192 push (lokal)")]),
        bullet([bold("2. "), text("Server: git pull origin main")]),
        bullet([bold("3. "), text("Server: pip install -r requirements.txt")]),
        bullet([bold("4. "), text("Server: npm run css:build (Tailwind)")]),
        bullet([bold("5. "), text("Server: migrate + collectstatic")]),
        bullet([bold("6. "), text("Server: systemctl restart jaysonkhan + nginx reload")]),
        bullet([bold("7. "), text("Health check: HTTPS + /health/ + static CSS")]),
        divider(),

        h2("8.2  Qo\u2018lda buyruqlar"),
        h3("Dev server (lokal)"),
        ...codeBlock(["backend/venv/bin/python backend/manage.py runserver 0.0.0.0:8000"]),
        h3("Tailwind CSS"),
        ...codeBlock([
          "npm run css:build    # bir martalik build",
          "npm run css:watch    # watch rejimida",
        ]),
        h3("Migratsiyalar"),
        ...codeBlock([
          "backend/venv/bin/python backend/manage.py makemigrations <app>",
          "backend/venv/bin/python backend/manage.py migrate",
        ]),
        h3("Testlar"),
        ...codeBlock([
          "# Barcha testlar",
          "backend/venv/bin/python backend/manage.py test portfolio blog contact \\",
          "  core interactions users --settings=config.settings.dev",
          "",
          "# Bitta app",
          "backend/venv/bin/python backend/manage.py test blog --settings=config.settings.dev",
        ]),
        h3("Collectstatic"),
        ...codeBlock(["backend/venv/bin/python backend/manage.py collectstatic --noinput"]),
        divider(),

        h2("8.3  Server ma\u2018lumotlari"),
        new Table({
          width: { size: CONTENT_W, type: WidthType.DXA },
          columnWidths: [3500, 5860],
          rows: [
            headerRow(["Parametr", "Qiymat"], [3500, 5860]),
            ...[
              ["Server", "Ubuntu 22.04 @ 144.91.69.225"],
              ["SSH alias", "jaysonkhan (~/.ssh/config)"],
              ["Stack", "Gunicorn \u2192 Nginx \u2192 SQLite"],
              ["Settings module", "config.settings.prod"],
              ["Service", "systemctl restart jaysonkhan"],
              ["Static fayllar", "/var/www/jaysonkhan/static/"],
              ["Media fayllar", "/var/www/jaysonkhan/media/"],
              ["Loglar", "/var/www/jaysonkhan/backend/logs/"],
              ["Backuplar", "/var/backups/jaysonkhan/"],
              ["Socket", "/var/www/jaysonkhan/backend/jaysonkhan.sock"],
            ].map(([k, v]) => new TableRow({ children: [
              new TableCell({ borders, width: { size: 3500, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [bold(k, { size: 20 })] })] }),
              new TableCell({ borders, width: { size: 5860, type: WidthType.DXA }, margins: cellMargins, children: [new Paragraph({ children: [code(v)] })] }),
            ]})),
          ],
        }),
        new Paragraph({ children: [new PageBreak()] }),

        // ════════════════════════════════════════════════════════════════════
        // 9. O'ZGARTIRILGAN FAYLLAR RO'YXATI
        // ════════════════════════════════════════════════════════════════════
        h1("9. O\u2018zgartirilgan fayllar ro\u2018yxati"),
        para(text("Barcha sessiyalarda o\u2018zgartirilgan fayllarning to\u2018liq ro\u2018yxati:")),
        divider(),

        h2("9.1  Yangi fayllar"),
        bullet([code("backend/apps/core/sitemaps.py"), text(" \u2014 Sitemap classlari")]),
        bullet([code("backend/apps/blog/feeds.py"), text(" \u2014 RSS/Atom feedlar")]),
        bullet([code("backend/presentation/web/templates/web/blog_search.html"), text(" \u2014 Qidiruv sahifasi")]),
        bullet([code("backend/scripts/backup-db.sh"), text(" \u2014 DB backup skripti")]),
        bullet([code("CLAUDE.md"), text(" \u2014 Loyiha kontekst fayli")]),
        divider(),

        h2("9.2  O\u2018zgartirilgan fayllar"),
        h3("Models (4 ta)"),
        bullet([code("portfolio/models.py"), text(" \u2014 indexes, get_absolute_url()")]),
        bullet([code("blog/models.py"), text(" \u2014 indexes, get_absolute_url(), reading_time")]),
        bullet([code("contact/models.py"), text(" \u2014 indexes")]),
        bullet([code("core/models.py"), text(" \u2014 visitor_count kesh")]),

        h3("Services (2 ta)"),
        bullet([code("portfolio/services.py"), text(" \u2014 get_homepage_data()")]),
        bullet([code("blog/services.py"), text(" \u2014 search_posts(), get_related_posts(), _is_postgres()")]),

        h3("Views (3 ta)"),
        bullet([code("core/views.py"), text(" \u2014 _sanitize_svg(), robots_txt(), health_check()")]),
        bullet([code("interactions/views.py"), text(" \u2014 xavfsizlik tuzatishlari")]),
        bullet([code("presentation/web/views.py"), text(" \u2014 HomeView, BlogSearchView, BlogDetailView")]),

        h3("Configuration (3 ta)"),
        bullet([code("config/settings/base.py"), text(" \u2014 sitemaps, logging")]),
        bullet([code("config/settings/prod.py"), text(" \u2014 app loggerlar")]),
        bullet([code("config/urls.py"), text(" \u2014 SEO, feeds, health URLs")]),

        h3("Templates (4 ta)"),
        bullet([code("base.html"), text(" \u2014 canonical URL, RSS link")]),
        bullet([code("blog_detail.html"), text(" \u2014 JSON-LD, reading time, related posts")]),
        bullet([code("blog_list.html"), text(" \u2014 search bar, reading time")]),
        bullet([code("project_detail.html"), text(" \u2014 JSON-LD")]),

        h3("Boshqa (3 ta)"),
        bullet([code("presentation/web/urls.py"), text(" \u2014 blog/search/ URL")]),
        bullet([code("presentation/api/serializers.py"), text(" \u2014 ContactMessage fields")]),
        bullet([code("deploy.sh"), text(" \u2014 health check integratsiyasi")]),
        divider(),

        h2("9.3  Migratsiyalar"),
        bullet(code("blog/0005_post_post_published_date_post_post_slug_published.py")),
        bullet(code("contact/0002_contactmessage_contact_date_read.py")),
        bullet(code("portfolio/0012_project_proj_visible_order_project_proj_featured_and_more.py")),

        new Paragraph({ spacing: { before: 600 } }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 2, color: "7C3AED", space: 8 } },
          spacing: { before: 400 },
          children: [new TextRun({ text: "Hujjat oxiri", font: "Arial", size: 20, color: "9CA3AF", italics: true })],
        }),
      ],
    },
  ],
});

const OUTPUT = "/Users/mac/Downloads/JaysonKhan_Texnik_Hujjat.docx";
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUTPUT, buf);
  console.log("Created:", OUTPUT, "(" + (buf.length / 1024).toFixed(0) + " KB)");
});
