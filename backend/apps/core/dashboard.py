"""Editorial admin dashboard data — KPI tiles, traffic chart, activity feed."""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone


def dashboard_callback(request, context):
    """Inject editorial KPI data into admin/index.html context."""
    from portfolio.models import Project, TeamMember
    from blog.models import Post
    from contact.models import ContactMessage
    from core.models import PageView, SiteSettings, Asset
    from interactions.models import Comment

    now = timezone.now()
    last_30 = now - timedelta(days=30)

    # ── KPI tiles ────────────────────────────────────────────────────────
    visitors_30 = PageView.objects.filter(created_at__gte=last_30).count()
    visitors_total = PageView.objects.count()
    inbox_unread = ContactMessage.objects.filter(is_read=False).count()
    inbox_total = ContactMessage.objects.count()

    assets_count = Asset.objects.count()
    size_total = Asset.objects.aggregate(total=Sum('size_bytes'))['total'] or 0
    assets_size_mb = round(size_total / 1024 / 1024, 1)

    posts_count = Post.objects.filter(is_published=True).count()
    projects_count = Project.objects.filter(is_visible=True).count()
    team_count = TeamMember.objects.filter(is_visible=True).count()
    comments_count = Comment.objects.filter(is_approved=True).count()

    # ── Traffic / 14d sparkline ──────────────────────────────────────────
    traffic_buckets = []
    for i in range(13, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = PageView.objects.filter(created_at__gte=day_start, created_at__lt=day_end).count()
        traffic_buckets.append({
            'day': day_start.strftime('%d'),
            'count': count,
            'is_today': i == 0,
        })

    max_traffic = max((b['count'] for b in traffic_buckets), default=1) or 1
    for b in traffic_buckets:
        b['height'] = max(8, int((b['count'] / max_traffic) * 180)) if max_traffic else 8

    # ── Activity feed ────────────────────────────────────────────────────
    activity = []
    for msg in ContactMessage.objects.order_by('-created_at')[:3]:
        activity.append({
            'kind': 'Inbox',
            'subject': msg.subject or msg.email,
            'detail': msg.email,
            'when': _humanize(now - msg.created_at),
            'ts': msg.created_at,
        })
    for post in Post.objects.filter(is_published=True).order_by('-created_at')[:3]:
        activity.append({
            'kind': 'Post published',
            'subject': post.title,
            'detail': post.category.name if post.category else 'Journal',
            'when': _humanize(now - post.created_at),
            'ts': post.created_at,
        })
    for proj in Project.objects.filter(is_visible=True).order_by('-created_at')[:3]:
        activity.append({
            'kind': 'Project',
            'subject': proj.title,
            'detail': 'Visible' if proj.is_visible else 'Hidden',
            'when': _humanize(now - proj.created_at),
            'ts': proj.created_at,
        })
    activity.sort(key=lambda a: a['ts'], reverse=True)
    activity = activity[:8]

    # ── Inject into Unfold context ───────────────────────────────────────
    context['jk_dashboard'] = {
        'tiles': [
            {'value': _fmt(visitors_30), 'label': 'Visitors / 30d', 'delta': f"{_fmt(visitors_total)} total", 'accent': True},
            {'value': str(assets_count), 'label': 'Assets', 'delta': f"{assets_size_mb} MB" if assets_count else 'empty', 'accent': False},
            {'value': str(inbox_unread), 'label': 'Inbox unread', 'delta': f"{inbox_total} total", 'accent': inbox_unread > 0},
            {'value': str(posts_count), 'label': 'Published posts', 'delta': f"{comments_count} comments", 'accent': False},
        ],
        'tiles_secondary': [
            {'value': str(projects_count), 'label': 'Projects'},
            {'value': str(team_count), 'label': 'Team members'},
        ],
        'traffic': traffic_buckets,
        'traffic_max': max_traffic,
        'activity': activity,
        'site_title': SiteSettings.load().site_title,
    }
    return context


def _fmt(n):
    """Compact number formatting: 14200 → 14.2k."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _humanize(td):
    """timedelta → '14m', '2h', '3d' style string."""
    sec = int(td.total_seconds())
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m"
    if sec < 86_400:
        return f"{sec // 3600}h"
    return f"{sec // 86_400}d"


# ── Sidebar badge counters ────────────────────────────────────────────────────
# Called on every admin page render — keep cheap. Return None if zero so
# Unfold hides the badge instead of showing "0".

def unread_messages_badge(request):
    """Count of unread Contact Messages — shown on Aloqa → Xabarlar."""
    try:
        from contact.models import ContactMessage
        n = ContactMessage.objects.filter(is_read=False).count()
        return str(n) if n else None
    except Exception:
        return None


def pending_comments_badge(request):
    """Count of comments awaiting approval — shown on Aloqa → Komentariyalar."""
    try:
        from interactions.models import Comment
        n = Comment.objects.filter(is_approved=False).count()
        return str(n) if n else None
    except Exception:
        return None
