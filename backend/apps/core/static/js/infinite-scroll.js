/**
 * Infinite Scroll Module
 * ──────────────────────────────────────────────────────────
 * Reusable fetch-more behavior using IntersectionObserver.
 *
 * Usage:
 *   InfiniteScroll.init({
 *     apiUrl:       '/api/projects/',
 *     gridId:       'items-grid',
 *     sentinelId:   'scroll-sentinel',
 *     spinnerId:    'scroll-spinner',
 *     renderItem:   (item) => '<div>...</div>',
 *     extraParams:  { platform: 'android' },  // optional
 *   });
 */
const InfiniteScroll = (() => {
    let page = 1;
    let loading = false;
    let hasNext = true;
    let config = {};

    function showSpinner() {
        const el = document.getElementById(config.spinnerId);
        if (el) el.style.display = 'flex';
    }

    function hideSpinner() {
        const el = document.getElementById(config.spinnerId);
        if (el) el.style.display = 'none';
    }

    function hideSentinel() {
        const el = document.getElementById(config.sentinelId);
        if (el) el.style.display = 'none';
    }

    async function fetchNextPage() {
        if (loading || !hasNext) return;
        loading = true;
        showSpinner();

        try {
            const params = new URLSearchParams({ page: page + 1 });
            if (config.extraParams) {
                Object.entries(config.extraParams).forEach(([k, v]) => {
                    if (v) params.set(k, v);
                });
            }

            const resp = await fetch(`${config.apiUrl}?${params.toString()}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

            const data = await resp.json();

            // DRF PageNumberPagination returns { count, next, previous, results }
            const items = data.results || data.items || [];
            hasNext = !!data.next;
            page += 1;

            const grid = document.getElementById(config.gridId);
            if (grid && items.length > 0) {
                const fragment = document.createDocumentFragment();
                items.forEach(item => {
                    const wrapper = document.createElement('div');
                    wrapper.innerHTML = config.renderItem(item).trim();
                    const el = wrapper.firstElementChild;
                    if (el) {
                        el.style.opacity = '0';
                        el.style.transform = 'translateY(20px)';
                        fragment.appendChild(el);
                    }
                });
                grid.appendChild(fragment);

                // Animate in
                requestAnimationFrame(() => {
                    grid.querySelectorAll('[style*="opacity: 0"]').forEach((el, i) => {
                        setTimeout(() => {
                            el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                            el.style.opacity = '1';
                            el.style.transform = 'translateY(0)';
                        }, i * 60);
                    });
                });
            }

            if (!hasNext) {
                hideSentinel();
                hideSpinner();
            }
        } catch (err) {
            console.error('InfiniteScroll fetch error:', err);
        } finally {
            loading = false;
            hideSpinner();
        }
    }

    function init(opts) {
        config = opts;
        page = 1;
        loading = false;
        hasNext = true;

        // Check initial server-side flag
        const grid = document.getElementById(config.gridId);
        if (grid && grid.dataset.hasNext === 'false') {
            hasNext = false;
            hideSentinel();
            hideSpinner();
            return;
        }

        const sentinel = document.getElementById(config.sentinelId);
        if (!sentinel) return;

        hideSpinner();

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && hasNext && !loading) {
                    fetchNextPage();
                }
            },
            { rootMargin: '200px' }
        );
        observer.observe(sentinel);
    }

    return { init };
})();
