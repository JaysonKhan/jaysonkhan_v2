---
name: web-backend-development
description: Guide for creating backend and web applications using Django, following Clean Architecture and Enterprise-Grade practices.
---

# Web & Backend Development Guidelines

This skill references the **Jaysonkhan Portfolio Platform** architecture. It is the comprehensive guide for building scalable, maintainable, and production-ready web applications using Python and Django.

## 1. Project Structure & Organization

### Directory Tree Reference
The project **MUST** follow this exact directory structure to ensure separation of concerns:

```text
PROJET_ROOT/
├── config/                 # Infrastructure Layer (Settings, WSGI, ASGI)
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py     # Shared settings (Auth, Apps, Middleware)
│   │   ├── dev.py      # Development-specific (Debug=True, SQLite)
│   │   └── prod.py     # Production-specific (Debug=False, Postgres, S3)
│   ├── __init__.py
│   ├── asgi.py
│   ├── urls.py         # Main URL entry point
│   └── wsgi.py
├── apps/                   # Domain Layer (Business Logic)
│   ├── __init__.py
│   ├── users/              # Example: Custom User Model
│   ├── content/            # Example: Content App
│   └── ...
├── presentation/           # Interface Layer
│   ├── api/                # DRF (Serializers, ViewSets, Routers)
│   └── web/                # SSR (Views, Forms, Templates, Static)
│       ├── templates/      # Project-level templates
│       └── static/         # Project-level static files (CSS, JS, Images)
├── .env                    # Environment variables (Never commit!)
├── .gitignore
├── manage.py
└── requirements.txt
```

## 2. Architectural Philosophy: Clean Architecture

### The `apps` Directory (Domain Layer)
- **Purpose**: Pure business logic and data definitions.
- **Rules**:
  - **Models (`models.py`)**: Define database schema here.
  - **Services (`services.py`)**: Encapsulate ALL business logic here. *Do not put logic in Views.*
  - **Selectors/Repositories**: Use these for complex queries strictly within services.
  - **NO Views**: Do not include `views.py` or API endpoints in these apps.

### The `presentation` Directory (Interface Layer)
- **Purpose**: Handling incoming requests and formatting responses.
- **Rules**:
  - **`api/`**: Django REST Framework code only.
    - `serializers.py`: Data validation and serialization.
    - `views.py` (ViewSets): Request handling logic only. Delegate work to `apps.services`.
    - `urls.py`: DRF Routers.
  - **`web/`**: Django Templates code.
    - `views.py`: Standard Django views returning `render()`.
    - `urls.py`: Web routing.

### The `config` Directory (Infrastructure Layer)
- **Purpose**: Configuration and routing.
- **Rules**:
  - Settings must be split into `base`, `dev`, and `prod`.
  - Use `django-environ` to read from `.env`.
  - **NEVER** hardcode secrets.

## 3. Implementation Patterns & Coding Standards

### Service Layer Pattern
**Problem**: Views becoming fat and untestable.
**Solution**: Logic lives in Services.

```python
# IMPROPER: Logic in View
def create_post(request):
    # logic mixed with HTTP
    if request.user.karm < 10: return Error()
    post = Post.objects.create(...)
    
# PROPER: Logic in Service (apps/blog/services.py)
class BlogService:
    def create_post(self, user, data):
        if user.karma < 10:
             raise ValidationError("Not enough karma")
        return Post.objects.create(author=user, **data)
```

### Stack & Tooling
- **Python**: 3.11+
- **Django**: 5.x (Latest)
- **API**: Django REST Framework (DRF)
- **Frontend**: Django Templates + TailwindCSS + HTMX (No heavy JS frameworks unless requested).
- **Linter**: `flake8`
- **Formatter**: `black`

## 4. Initialization Workflow
When creating a new project with this skill:
1.  Initialize standard Django project.
2.  Create `apps`, `config`, `presentation` directories immediately.
3.  Move inner project folder contents to `config`.
4.  Update `manage.py` and `wsgi.py` to point to `config.settings.dev`.
5.  Setup `django-environ` and `.env` file.
