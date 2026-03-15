/**
 * OSINT Core — shared utility functions
 * Used by: osint-profile.js, osint-entity.js, osint-search.js
 */

/* ── XSS-safe HTML escaping ──────────────────────────────────────── */

function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

/* ── Date formatting ─────────────────────────────────────────────── */

function formatDate(s) {
    if (!s) return '<span class="rb-muted">\u2014</span>';
    return s.substring(0, 10) + ' ' + s.substring(11, 16);
}

/* ── Key formatting (snake_case → Title Case) ────────────────────── */

function formatKey(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, function(l) { return l.toUpperCase(); });
}

/* ── Views/forwards short format (1200 → 1.2K) ──────────────────── */

function fmtViews(n) {
    if (n == null) return '';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
}
