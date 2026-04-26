"""Prod-aware fix: normalize the xo column + apply hand translations.

Initial 0007 was a no-op on rows whose initial backfill copied the source
language into uz/ru/en (and left xo empty). Two passes here:

1) Normalize xo: if `_xo` is empty, copy from the first non-empty among
   (`_uz`, `_ru`, `_en`, bare). This makes xo the canonical source.
2) For posts keyed by SLUG: if a target lang's column is empty OR equal to
   the xo value (i.e. an unrtranslated duplicate from the initial backfill),
   overwrite with the hand translation. Real admin-edited translations are
   preserved.
"""
from django.db import migrations


CATEGORY_TRANSLATIONS = {
    "Development": {"xo": "Dasturlash", "uz": "Dasturlash",
                    "ru": "Разработка", "en": "Development"},
}

TAG_TRANSLATIONS = {
    "Portfolio": {"xo": "Portfolio", "uz": "Portfolio",
                  "ru": "Портфолио", "en": "Portfolio"},
    "Web Development": {"xo": "Web dasturlash", "uz": "Web dasturlash",
                        "ru": "Веб-разработка", "en": "Web Development"},
}


# Keyed by post slug — slugs are stable across local/prod, ids aren't.
POST_TRANSLATIONS_BY_SLUG = {
    "mastering-flutter-3-x": {
        "title": {
            "xo": "Flutter 3.x ni puxta o'rganish",
            "uz": "Flutter 3.x ni puxta o'rganish",
            "ru": "Глубокое погружение в Flutter 3.x",
            "en": "Mastering Flutter 3.x",
        },
        "excerpt": {
            "xo": "Flutter widgetlari va unumdorligi haqida chuqur tahlil.",
            "uz": "Flutter widgetlari va unumdorligi haqida chuqur tahlil.",
            "ru": "Глубокий разбор виджетов и производительности Flutter.",
            "en": "A deep dive into Flutter widgets and performance.",
        },
    },
    "clean-architecture-in-django": {
        "title": {
            "xo": "Django'da Clean Architecture",
            "uz": "Django'da Clean Architecture",
            "ru": "Clean Architecture в Django",
            "en": "Clean Architecture in Django",
        },
        "excerpt": {
            "xo": "Django ilovalaringizni miqyoslash uchun qanday tuzilmalash kerak.",
            "uz": "Django ilovalaringizni miqyoslash uchun qanday tuzilmalash kerak.",
            "ru": "Как структурировать Django-приложения для масштабирования.",
            "en": "How to structure your Django apps for scale.",
        },
    },
    "men-oz-portfolio-web-saytimni-ishga-tushirdim": {
        "title": {
            "xo": "Men o'z portfolio web saytimni ishga tushirdim",
            "uz": "Men o'z portfolio web saytimni ishga tushirdim",
            "ru": "Я запустил свой портфолио-сайт",
            "en": "I launched my portfolio website",
        },
        "excerpt": {
            "xo": (
                "jaysonkhan.com — mening professional portfolio saytim rasman ishga tushdi. "
                "Saytda loyihalar, blog, texnik ko'nikmalar, Telegram integratsiya va boshqa "
                "ko'plab imkoniyatlar mavjud."
            ),
            "uz": (
                "jaysonkhan.com — mening professional portfolio saytim rasman ishga tushdi. "
                "Saytda loyihalar, blog, texnik ko'nikmalar, Telegram integratsiya va boshqa "
                "ko'plab imkoniyatlar mavjud."
            ),
            "ru": (
                "jaysonkhan.com — мой профессиональный портфолио-сайт официально запущен. "
                "На сайте — проекты, блог, технические навыки, Telegram-интеграция и многое другое."
            ),
            "en": (
                "jaysonkhan.com — my professional portfolio site is officially live. "
                "It features projects, a blog, technical skills, Telegram integration, "
                "and a lot more."
            ),
        },
        "content_rich": {
            "ru": """<h2>Введение</h2>
<p>Здравствуйте! Я официально запустил свой портфолио-сайт — <b>jaysonkhan.com</b>. Это профессиональная платформа, на которой собраны мой опыт разработки, проекты и технические навыки. В этой статье подробно разберём, что есть на сайте.</p>

<h2>Главная страница — первое впечатление</h2>
<p>Главная страница состоит из нескольких ключевых секций. На самом верху расположен <b>Hero Section</b> — короткая презентация моей специализации, анимированный typing-эффект и основные CTA-кнопки. Кнопка «View Apps» ведёт к проектам, «Contact Me» — на страницу контактов.</p>
<p>Слева — орбитальная анимация с иконками технологий, наглядно отражающая мои ключевые навыки.</p>

<h2>Обо мне</h2>
<p>В блоке About подробно описан мой профессиональный опыт. Я Python backend-архитектор с 5+ годами опыта. Профессионально работаю с Django, FastAPI, PostgreSQL, Redis и Docker. Проектирую высокопроизводительные backend-системы, придерживаясь принципов Clean Architecture и SOLID.</p>

<h2>Статистика</h2>
<p>На сайте — анимированные счётчики моих профессиональных достижений:</p>
<ul>
    <li><b>3+ года</b> — профессиональный опыт</li>
    <li><b>30+</b> — выпущенных приложений</li>
    <li><b>1M+</b> — суммарных загрузок</li>
    <li><b>100%</b> — соответствие принципам Clean Architecture</li>
</ul>

<h2>Технические навыки</h2>
<p>В разделе My Expertise можно увидеть мой технологический стек. Каждый навык сгруппирован по категории и имеет индикатор уровня:</p>
<ul>
    <li><b>Architecture:</b> Clean Architecture, BLoC, Provider — проектирование архитектуры систем</li>
    <li><b>Backend &amp; Networking:</b> Python, Django, FastAPI — серверная разработка</li>
    <li><b>Databases:</b> PostgreSQL, Redis — работа с базами данных</li>
    <li><b>DevOps &amp; Tools:</b> Docker, CI/CD — деплой и автоматизация</li>
    <li><b>Security:</b> OAuth 2.0, Pentesting — безопасность и аутентификация</li>
    <li><b>UI/UX:</b> Figma — дизайн и пользовательский опыт</li>
</ul>

<h2>Проекты — мои работы</h2>
<p>На странице <b>/projects/</b> собраны все мои проекты. Их можно фильтровать по 6 категориям:</p>
<ul>
    <li><b>All</b> — все проекты</li>
    <li><b>Cross-platform</b> — приложения на нескольких платформах</li>
    <li><b>Android</b> — приложения в Google Play</li>
    <li><b>iOS</b> — приложения в App Store</li>
    <li><b>Web</b> — веб-приложения</li>
    <li><b>Telegram Bot</b> — Telegram-боты</li>
</ul>
<p>Каждая страница проекта содержит подробную информацию, использованные технологии, ссылки на App Store и Google Play, а также секцию case study (проблема, решение, результат).</p>
<p>На главной странице самые важные проекты вынесены в блок <b>Featured Projects</b>.</p>

<h2>Блог — технические статьи</h2>
<p>Раздел блога, который вы сейчас читаете, — также важная часть сайта. Здесь я пишу о разработке, архитектуре и технологиях. Возможности блога:</p>
<ul>
    <li><b>Категории и теги</b> — фильтрация статей по темам</li>
    <li><b>Поиск</b> — полнотекстовый поиск (PostgreSQL full-text search)</li>
    <li><b>Время чтения</b> — оценка для каждой статьи</li>
    <li><b>Оглавление</b> — автоматически сгенерированное Table of Contents</li>
    <li><b>Шеринг</b> — кнопки для Twitter, LinkedIn, Telegram и копирования ссылки</li>
    <li><b>Прогресс чтения</b> — progress bar в верхней части страницы</li>
    <li><b>Похожие статьи</b> — посты по близким темам</li>
</ul>

<h2>Комментарии и интерактив</h2>
<p>На каждой странице блог-поста и проекта есть интерактивный блок:</p>
<ul>
    <li><b>Комментарии</b> — оставлять можно после входа через Telegram. Поддерживаются вложенные комментарии</li>
    <li><b>Like</b> — можно лайкнуть статью или проект</li>
    <li><b>Реакции</b> — emoji-реакции на комментарии</li>
</ul>
<p>Все комментарии проходят модерацию — это защита от спама и неприемлемого контента.</p>

<h2>Telegram-интеграция</h2>
<p>Сайт глубоко интегрирован с Telegram:</p>
<ul>
    <li><b>Telegram Login</b> — вход через Telegram (с проверкой HMAC)</li>
    <li><b>Mini App</b> — полноценный просмотр сайта внутри Telegram</li>
    <li><b>Deep Links</b> — переход из бота прямо на нужную статью или проект</li>
    <li><b>Шаринг в канал</b> — публикация контента в Telegram-канал в один клик из админки</li>
    <li><b>Уведомления</b> — админ получает уведомление в Telegram-группу о новых комментариях, лайках, заявках</li>
</ul>

<h2>Контакты</h2>
<p>На странице <b>/contact/</b> есть форма обратной связи. Форма защищена honeypot-проверкой и rate-limiting'ом по IP. После отправки сообщения мне моментально приходит уведомление в Telegram.</p>

<h2>Технический стек</h2>
<p>Сайт построен на следующих технологиях:</p>
<ul>
    <li><b>Django 4.2</b> — backend-фреймворк</li>
    <li><b>Django REST Framework</b> — API-слой</li>
    <li><b>Tailwind CSS</b> — современный responsive-дизайн</li>
    <li><b>PostgreSQL</b> — надёжная база данных</li>
    <li><b>Gunicorn + Nginx</b> — production-сервер</li>
    <li><b>Clean Architecture</b> — структура кода (паттерн Repository + Service)</li>
</ul>
<p>Сайт полностью адаптивный — корректно отображается на смартфоне, планшете и десктопе.</p>

<h2>Заключение</h2>
<p>Этот портфолио-сайт не только демонстрирует мои работы, но и сам является постоянно развивающимся проектом. Новые проекты, статьи и функции добавляются регулярно. Изучайте сайт и оставляйте комментарии!</p>
<p>Если есть вопросы — пишите через <a href="/contact/">страницу контактов</a>. Подписывайтесь на мой Telegram-канал!</p>""",
            "en": """<h2>Introduction</h2>
<p>Hello! I've officially launched my portfolio website — <b>jaysonkhan.com</b>. It's a professional platform that brings together my development experience, projects, and technical skills. In this article we'll walk through what the site offers.</p>

<h2>Home — first impression</h2>
<p>The home page is built from a few key sections. At the very top sits the <b>Hero Section</b> — a short pitch about what I do, an animated typing effect, and the main call-to-action buttons. "View Apps" leads to my projects; "Contact Me" opens the contact page.</p>
<p>On the left there's an orbital animation with technology icons that visually represents my core skills.</p>

<h2>About me</h2>
<p>The About section walks through my professional background. I'm a Python backend architect with 5+ years of experience. I work professionally with Django, FastAPI, PostgreSQL, Redis, and Docker. I design high-performance backend systems following Clean Architecture and SOLID principles.</p>

<h2>Statistics</h2>
<p>The site shows animated counters reflecting my professional milestones:</p>
<ul>
    <li><b>3+ years</b> — professional experience</li>
    <li><b>30+</b> — apps shipped</li>
    <li><b>1M+</b> — total downloads</li>
    <li><b>100%</b> — adherence to Clean Architecture principles</li>
</ul>

<h2>Technical skills</h2>
<p>The My Expertise section shows my full technology stack. Each skill is grouped by category with a level indicator:</p>
<ul>
    <li><b>Architecture:</b> Clean Architecture, BLoC, Provider — system architecture design</li>
    <li><b>Backend &amp; Networking:</b> Python, Django, FastAPI — server-side development</li>
    <li><b>Databases:</b> PostgreSQL, Redis — data layer</li>
    <li><b>DevOps &amp; Tools:</b> Docker, CI/CD — deployment and automation</li>
    <li><b>Security:</b> OAuth 2.0, Pentesting — security and authentication</li>
    <li><b>UI/UX:</b> Figma — design and user experience</li>
</ul>

<h2>Projects — my work</h2>
<p>The <b>/projects/</b> page lists all of my projects. They can be filtered across 6 categories:</p>
<ul>
    <li><b>All</b> — every project</li>
    <li><b>Cross-platform</b> — apps that run on multiple platforms</li>
    <li><b>Android</b> — apps published on Google Play</li>
    <li><b>iOS</b> — apps published on the App Store</li>
    <li><b>Web</b> — web applications</li>
    <li><b>Telegram Bot</b> — Telegram bots</li>
</ul>
<p>Each project page includes detailed info, the tech stack used, App Store and Google Play links, plus a case study section (problem, solution, results).</p>
<p>On the home page, the most important projects are highlighted in the <b>Featured Projects</b> block.</p>

<h2>Blog — technical writing</h2>
<p>The blog you're reading right now is another central part of the site. I write here about development, architecture, and technology. Blog features include:</p>
<ul>
    <li><b>Categories and tags</b> — filter articles by topic</li>
    <li><b>Search</b> — full-text search (PostgreSQL FTS)</li>
    <li><b>Reading time</b> — estimated time per article</li>
    <li><b>Table of contents</b> — auto-generated from headings</li>
    <li><b>Share buttons</b> — Twitter, LinkedIn, Telegram, copy link</li>
    <li><b>Reading progress</b> — a progress bar at the top of the page</li>
    <li><b>Related articles</b> — posts on similar topics</li>
</ul>

<h2>Comments and interactivity</h2>
<p>Every blog post and project page has an interactive section:</p>
<ul>
    <li><b>Comments</b> — sign in via Telegram and leave a comment. Threaded replies are supported</li>
    <li><b>Like button</b> — like an article or project</li>
    <li><b>Reactions</b> — emoji reactions on comments</li>
</ul>
<p>All comments are moderated — this protects against spam and inappropriate content.</p>

<h2>Telegram integration</h2>
<p>The site is deeply integrated with Telegram:</p>
<ul>
    <li><b>Telegram Login</b> — sign in via Telegram (HMAC-verified)</li>
    <li><b>Mini App</b> — browse the site fully inside Telegram</li>
    <li><b>Deep links</b> — jump straight from the bot to a specific article or project</li>
    <li><b>Channel sharing</b> — admin can post content to a Telegram channel with a single click</li>
    <li><b>Notifications</b> — new comments, likes, and contact messages ping the admin group</li>
</ul>

<h2>Contact</h2>
<p>The <b>/contact/</b> page has a message form. The form is protected with a honeypot and IP-based rate limiting. As soon as a message is sent, I get an instant Telegram notification.</p>

<h2>Technical infrastructure</h2>
<p>The site is built on the following stack:</p>
<ul>
    <li><b>Django 4.2</b> — backend framework</li>
    <li><b>Django REST Framework</b> — API layer</li>
    <li><b>Tailwind CSS</b> — modern responsive design</li>
    <li><b>PostgreSQL</b> — reliable database</li>
    <li><b>Gunicorn + Nginx</b> — production server</li>
    <li><b>Clean Architecture</b> — code structure (Repository + Service pattern)</li>
</ul>
<p>The site is fully responsive — it looks great on phone, tablet, and desktop.</p>

<h2>Wrap-up</h2>
<p>This portfolio site doesn't just showcase my work — it's also a constantly evolving project of my own. New projects, articles, and features are added regularly. Take a look around and leave a comment with your thoughts!</p>
<p>Have questions? Drop me a line via the <a href="/contact/">contact page</a>. And subscribe to my Telegram channel!</p>""",
        },
    },
}


LANGS = ("xo", "uz", "ru", "en")
ALT_LANGS = ("uz", "ru", "en")  # used to backfill xo


def _normalize_xo(obj, fields):
    """If `_xo` is empty, copy the first non-empty alt language (or bare field).

    Returns set of field names whose `_xo` got populated.
    """
    populated = set()
    for f in fields:
        cur_xo = getattr(obj, f"{f}_xo", None)
        if cur_xo:
            continue
        # Try alt langs first
        candidate = None
        for alt in ALT_LANGS:
            v = getattr(obj, f"{f}_{alt}", None)
            if v:
                candidate = v
                break
        if not candidate:
            candidate = getattr(obj, f, None)
        if candidate:
            setattr(obj, f"{f}_xo", candidate)
            populated.add(f)
    return populated


def _apply_translations(obj, by_field_lang):
    """For each (field, lang) translation: write it if the current column is
    empty OR equal to `_xo` (an unrtranslated duplicate from initial backfill).
    Real admin-translated values (different from xo) are preserved.
    """
    for field, by_lang in by_field_lang.items():
        xo_val = getattr(obj, f"{field}_xo", None) or ""
        for lang, value in by_lang.items():
            attr = f"{field}_{lang}"
            cur = getattr(obj, attr, None) or ""
            if not cur or cur == xo_val:
                setattr(obj, attr, value)


def fix_translations(apps, schema_editor):
    Category = apps.get_model("blog", "Category")
    Tag = apps.get_model("blog", "Tag")
    Post = apps.get_model("blog", "Post")

    # ── Categories ────────────────────────────────────────────────────────────
    for c in Category.objects.all():
        _normalize_xo(c, ["name"])
        canonical = c.name_xo or c.name or ""
        translations = CATEGORY_TRANSLATIONS.get(canonical) or {
            lang: canonical for lang in LANGS
        }
        _apply_translations(c, {"name": translations})
        c.save()

    # ── Tags ──────────────────────────────────────────────────────────────────
    for t in Tag.objects.all():
        _normalize_xo(t, ["name"])
        canonical = t.name_xo or t.name or ""
        translations = TAG_TRANSLATIONS.get(canonical) or {
            lang: canonical for lang in LANGS
        }
        _apply_translations(t, {"name": translations})
        t.save()

    # ── Posts ─────────────────────────────────────────────────────────────────
    for p in Post.objects.all():
        _normalize_xo(p, ["title", "excerpt", "content_rich"])
        cfg = POST_TRANSLATIONS_BY_SLUG.get(p.slug)
        if cfg:
            _apply_translations(p, cfg)
        # Mirror xo into any still-empty langs so language switcher never shows blank
        for field in ("title", "excerpt", "content_rich"):
            xo_val = getattr(p, f"{field}_xo", None) or ""
            if not xo_val:
                continue
            for lang in ALT_LANGS:
                attr = f"{field}_{lang}"
                if not getattr(p, attr, None):
                    setattr(p, attr, xo_val)
        p.save()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0007_seed_translations"),
    ]

    operations = [
        migrations.RunPython(fix_translations, reverse_noop),
    ]
