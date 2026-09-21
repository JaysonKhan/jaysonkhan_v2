document.addEventListener('DOMContentLoaded', function() {
    if (typeof InfiniteScroll === 'undefined') return;

    function esc(s) {
        var d = document.createElement('div');
        d.appendChild(document.createTextNode(s != null ? String(s) : ''));
        return d.innerHTML;
    }

    var grid = document.getElementById("items-grid");
    var projectsBase = grid.dataset.projectsUrl;
    var KIND_LABELS = { web: 'WEB', bot: 'TG BOT', mobile: 'MOBILE' };

    var urlParams = new URLSearchParams(window.location.search);
    var filterKey = urlParams.get('filter') || '';
    var extraParams = {};
    if (filterKey) extraParams.filter = filterKey;
    var search = urlParams.get("q") || "";
    if (search) extraParams.q = search;

    InfiniteScroll.init({
        apiUrl: grid.dataset.apiUrl,
        gridId: 'items-grid',
        sentinelId: 'scroll-sentinel',
        spinnerId: 'scroll-spinner',
        extraParams: extraParams,
        renderItem: function(p) {
            var kind = p.kind || (p.is_bot ? 'bot' : (p.web_page_url ? 'web' : 'mobile'));
            var year = (p.created_at || '').slice(0, 4) || '';
            var tech = (p.tech_tags || []).slice(0, 4).map(function(t) {
                return '<span class="tag">' + esc(t) + '</span>';
            }).join('');
            var stats = (p.stats || []).slice(0, 3).map(function(s) {
                return '<div class="proj-stat"><span class="proj-stat__v">' + esc(s.v) + '</span><span class="proj-stat__l">' + esc(s.l) + '</span></div>';
            }).join('');
            var href = projectsBase + esc(p.slug) + '/';
            var asof = p.stats_as_of ? '<p class="project-asof mono-label">' + esc(grid.dataset.asofLabel) + ' <time datetime="' + esc(p.stats_as_of) + '">' + esc(p.stats_as_of) + '</time></p>' : '';
            return '<a href="' + href + '" class="card proj-card reveal in">' +
                '<div class="proj-card__top">' +
                '<span class="tag kind-badge--' + esc(kind) + '">' + (KIND_LABELS[kind] || '—') + '</span>' +
                '<span class="proj-card__year">' + esc(year) + '</span>' +
                '</div>' +
                '<h2 class="proj-title">' + esc(p.title) + '</h2>' +
                '<p class="proj-card__desc">' + esc(p.description || '') + '</p>' +
                '<div class="proj-card__tech">' + tech + '</div>' +
                asof + '<div class="proj-card__foot">' +
                '<div class="proj-card__stats">' + stats + '</div>' +
                '<span class="proj-card__arrow"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7M8 7h9v9"/></svg></span>' +
                '</div></a>';
        }
    });
});
