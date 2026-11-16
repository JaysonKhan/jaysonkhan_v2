"""robots.txt guards — internal search results stay out of every search-engine group.

2026-11-09 Search Console alert: Googlebot crawled the literal SearchAction template
`/<lang>/blog/search/?q={search_term_string}` (WebSite JSON-LD) and filed it as a Soft 404.
A named `User-agent` group replaces `*`, so the rule must be present in each group.
"""
from core.views import robots_txt
from django.test import RequestFactory, SimpleTestCase

SEARCH_RULE = 'Disallow: /*/blog/search/'


def _groups(text):
    """{'googlebot': [rule lines], …} — one entry per User-agent block."""
    groups, agents, rules = {}, [], []
    for raw in text.splitlines():
        line = raw.strip()
        if line.lower().startswith('user-agent:'):
            if rules:
                agents, rules = [], []
            agents.append(line.split(':', 1)[1].strip().lower())
            for agent in agents:
                groups[agent] = rules
        elif line and not line.startswith('#') and agents:
            rules.append(line)
    return groups


class RobotsSearchPagesTests(SimpleTestCase):
    def setUp(self):
        request = RequestFactory().get('/robots.txt', HTTP_HOST='jaysonkhan.com', secure=True)
        self.groups = _groups(robots_txt(request).content.decode())

    def test_search_results_are_closed_for_search_engines(self):
        for agent in ('*', 'googlebot', 'bingbot', 'yandexbot', 'duckduckbot', 'applebot'):
            self.assertIn(SEARCH_RULE, self.groups[agent], agent)

    def test_public_pages_stay_open(self):
        for agent in ('*', 'googlebot', 'bingbot', 'yandexbot'):
            self.assertIn('Allow: /', self.groups[agent], agent)
            self.assertNotIn('Disallow: /', self.groups[agent], agent)
