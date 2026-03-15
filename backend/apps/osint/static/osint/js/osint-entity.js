/**
 * OSINT Entity Profile — channel messages, search, pagination
 * Requires: osint-core.js (escapeHtml, formatDate, fmtViews)
 * Config globals: ENTITY_ID, MESSAGES_URL, SEARCH_URL, PROFILE_URL_TPL, MSG_PHOTO_URL_TPL
 * Optional: window._funstatData (set inline when FunStat data is available)
 */

var _nextMessageOffset = 0;
var _searchQuery = '';
var _nextSearchOffset = 0;

/* ── FunStat data rendering ──────────────────────────────────────── */

function renderFunstatData(data) {
    var container = document.getElementById('funstat-data');
    if (!container) return;
    if (!data || (typeof data === 'object' && Object.keys(data).length === 0)) {
        container.innerHTML = '<div class="rb-muted" style="padding:0.5rem;">Ma\'lumot topilmadi</div>';
        return;
    }
    var html = '<div class="rb-table-wrap"><table class="rb-table"><tbody>';
    var keys = Object.keys(data);
    for (var i = 0; i < keys.length; i++) {
        var val = data[keys[i]];
        if (val === null || val === undefined) val = '\u2014';
        else if (typeof val === 'boolean') val = val ? 'Ha' : 'Yo\'q';
        else if (typeof val === 'object') val = JSON.stringify(val);
        else val = String(val);
        html += '<tr><td class="rb-muted" style="width:220px;font-weight:600;">' +
            escapeHtml(formatKey(keys[i])) +
            '</td><td>' + escapeHtml(val) + '</td></tr>';
    }
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

/* ── Message row renderer ────────────────────────────────────────── */

function renderMessageRow(msg) {
    // Text — prefer text_html (with Telegram formatting), fallback to escaped plain text
    var textContent = msg.text_html ? sanitizeHtml(msg.text_html) : escapeHtml(msg.text || '');

    // Photo — inline image for photo media
    var photoHtml = '';
    if (msg.has_media && msg.media_type === 'photo') {
        var photoUrl = MSG_PHOTO_URL_TPL.replace('7777788888', msg.id);
        photoHtml = '<div class="msg-photo">' +
            '<img src="' + photoUrl + '" alt="" loading="lazy" ' +
            'onclick="window.open(this.src, \'_blank\')" ' +
            'onerror="this.parentNode.style.display=\'none\'">' +
            '</div>';
    }

    // Non-photo media badge
    var mediaBadge = '';
    if (msg.has_media && msg.media_type && msg.media_type !== 'photo') {
        var mediaIcons = {
            'document': 'description', 'webpage': 'language',
            'location': 'location_on', 'contact': 'person', 'poll': 'poll',
            'video': 'videocam', 'voice': 'mic', 'sticker': 'emoji_emotions',
            'dice': 'casino', 'venue': 'place', 'game': 'sports_esports'
        };
        var icon = mediaIcons[msg.media_type] || 'attachment';
        mediaBadge = '<span class="msg-media-badge">' +
            '<span class="material-symbols-outlined" style="font-size:11px;">' + icon + '</span>' +
            msg.media_type + '</span>';
    }

    // Views
    var viewsHtml = '';
    if (msg.views != null) {
        viewsHtml = '<span class="msg-views">' +
            '<span class="material-symbols-outlined" style="font-size:11px;">visibility</span>' +
            fmtViews(msg.views) + '</span>';
    }

    // Forwards
    var fwdHtml = '';
    if (msg.forwards) {
        fwdHtml = '<span class="msg-views">' +
            '<span class="material-symbols-outlined" style="font-size:11px;">forward</span>' +
            fmtViews(msg.forwards) + '</span>';
    }

    return '<div class="msg-row">' +
        '<div class="msg-meta">' +
            '<span class="msg-id">#' + msg.id + '</span>' +
            mediaBadge +
            '<span style="margin-left:auto;">' + formatDate(msg.date) + '</span>' +
            viewsHtml +
            fwdHtml +
        '</div>' +
        (textContent ? '<div class="msg-text">' + textContent + '</div>' : '') +
        photoHtml +
    '</div>';
}

/* ── Messages loading ────────────────────────────────────────────── */

function loadMessages(offsetId, refresh) {
    var container = document.getElementById('messages-container');
    var loadMore = document.getElementById('messages-load-more');
    loadMore.style.display = 'none';

    if (offsetId === 0) {
        container.innerHTML = '<div class="loading"><span class="material-symbols-outlined spin" style="font-size:20px;">autorenew</span></div>';
    } else {
        container.insertAdjacentHTML('beforeend',
            '<div class="loading" id="msg-loading"><span class="material-symbols-outlined spin" style="font-size:18px;">autorenew</span></div>');
    }

    var url = MESSAGES_URL + '?offset_id=' + offsetId + '&limit=20';
    if (refresh) url += '&refresh=1';

    fetch(url)
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var existingLoading = document.getElementById('msg-loading');
            if (existingLoading) existingLoading.remove();

            if (d.error) {
                if (offsetId === 0) {
                    container.innerHTML = buildErrorCard(d.error, "loadMessages(0, true)");
                }
                return;
            }

            var messages = d.data ? d.data.messages : [];
            if (!messages || messages.length === 0) {
                if (offsetId === 0) {
                    container.innerHTML = '<div class="rb-muted" style="padding:1rem; text-align:center;">Xabarlar topilmadi</div>';
                }
                return;
            }

            var html = '';
            for (var i = 0; i < messages.length; i++) {
                html += renderMessageRow(messages[i]);
            }

            if (offsetId === 0) {
                container.innerHTML = '';
                var cacheHtml = '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.25rem;">';
                cacheHtml += '<span class="rb-cache-badge ' + (d.cached ? 'fresh' : 'stale') + '">' +
                    '<span class="material-symbols-outlined" style="font-size:12px;">' + (d.cached ? 'cached' : 'sync') + '</span> ' +
                    (d.cached ? 'Keshdan' : 'Yangi') + '</span>';
                cacheHtml += '<span class="rb-muted" style="font-size:0.6875rem;">' + (d.data.count || 0) + ' ta xabar</span>';
                cacheHtml += '</div>';
                container.innerHTML = cacheHtml;
            }
            container.insertAdjacentHTML('beforeend', html);

            _nextMessageOffset = d.data.next_offset_id || 0;
            if (d.data.has_more && _nextMessageOffset > 0) {
                loadMore.style.display = 'block';
            }
        })
        .catch(function() {
            if (offsetId === 0) {
                container.innerHTML = buildErrorCard('Ulanish xatosi (0)', "loadMessages(0, true)");
            }
        });
}

function loadMoreMessages() {
    if (_nextMessageOffset > 0) {
        loadMessages(_nextMessageOffset, false);
    }
}

/* ── Channel search ──────────────────────────────────────────────── */

document.getElementById('channel-search-form').addEventListener('submit', function(e) {
    e.preventDefault();
    var q = document.getElementById('channel-search-q').value.trim();
    if (!q) return;
    _searchQuery = q;
    _nextSearchOffset = 0;
    searchMessages(q, 0);
});

function searchMessages(query, offsetId) {
    var container = document.getElementById('search-results');
    var loadMore = document.getElementById('search-load-more');
    loadMore.style.display = 'none';

    if (offsetId === 0) {
        container.innerHTML = '<div class="loading"><span class="material-symbols-outlined spin" style="font-size:20px;">autorenew</span></div>';
    }

    fetch(SEARCH_URL + '?q=' + encodeURIComponent(query) + '&offset_id=' + offsetId + '&limit=20')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.error) {
                container.innerHTML = buildErrorCard(d.error);
                return;
            }

            var messages = d.data ? d.data.messages : [];
            if (!messages || messages.length === 0) {
                if (offsetId === 0) {
                    container.innerHTML = '<div class="rb-muted" style="padding:1rem; text-align:center;">"' + escapeHtml(query) + '" bo\'yicha natija topilmadi</div>';
                }
                return;
            }

            var html = '';
            for (var i = 0; i < messages.length; i++) {
                html += renderMessageRow(messages[i]);
            }

            if (offsetId === 0) {
                container.innerHTML = '<div style="margin-bottom:0.25rem;"><span class="rb-muted" style="font-size:0.75rem;">' +
                    '"' + escapeHtml(query) + '" uchun ' + (d.data.count || 0) + ' ta natija</span></div>';
            }
            container.insertAdjacentHTML('beforeend', html);

            _nextSearchOffset = d.data.next_offset_id || 0;
            if (d.data.has_more && _nextSearchOffset > 0) {
                loadMore.style.display = 'block';
            }
        })
        .catch(function() {
            container.innerHTML = buildErrorCard('Ulanish xatosi (0)');
        });
}

function loadMoreSearchResults() {
    if (_nextSearchOffset > 0 && _searchQuery) {
        searchMessages(_searchQuery, _nextSearchOffset);
    }
}

/* ── Auto-load on page ready ─────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', function() {
    // Render FunStat data if available
    if (window._funstatData) {
        renderFunstatData(window._funstatData);
    }
    // Load messages
    loadMessages(0, false);
});
