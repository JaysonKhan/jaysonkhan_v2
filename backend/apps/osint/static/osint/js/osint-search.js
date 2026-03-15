/**
 * OSINT Search — text search AJAX handler
 * Requires: osint-core.js (escapeHtml)
 * Config globals: TEXT_SEARCH_URL, PROFILE_URL_TPL
 */

document.getElementById('text-search-form').addEventListener('submit', function(e) {
    e.preventDefault();
    var q = document.getElementById('text-q').value.trim();
    if (!q) return;
    var container = document.getElementById('text-results');
    container.innerHTML = '<div class="loading"><span class="material-symbols-outlined spin">autorenew</span> Qidirilmoqda...</div>';

    fetch(TEXT_SEARCH_URL + '?q=' + encodeURIComponent(q))
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.error) {
                var errDiv = document.createElement('div');
                errDiv.className = 'rb-error-box';
                errDiv.textContent = d.error;
                container.innerHTML = '';
                container.appendChild(errDiv);
                return;
            }
            var items = d.data;
            if (items && items.data) items = items.data;
            if (!items || (Array.isArray(items) && items.length === 0)) {
                container.innerHTML = '<div class="rb-muted" style="padding:1rem;">Natijalar topilmadi</div>';
                return;
            }
            if (!Array.isArray(items)) items = [items];

            var html = '<div class="rb-table-wrap"><table class="rb-table"><thead><tr><th>Matn</th><th>User</th><th>Guruh</th><th>Sana</th></tr></thead><tbody>';
            items.forEach(function(item) {
                var userId = item.user_id || '';
                var text = item.text || '-';
                if (text.length > 120) text = text.substring(0, 120) + '...';
                var groupTitle = '';
                if (item.group) groupTitle = item.group.title || '';
                html += '<tr>' +
                    '<td style="max-width:300px;word-break:break-word;">' + escapeHtml(text) + '</td>' +
                    '<td><a href="' + PROFILE_URL_TPL.replace('99999', escapeHtml(String(userId))) + '">' +
                    escapeHtml(item.name || item.username || String(userId) || '-') + '</a></td>' +
                    '<td class="rb-muted">' + escapeHtml(groupTitle) + '</td>' +
                    '<td class="rb-muted" style="white-space:nowrap;">' + escapeHtml(item.date || '-') + '</td>' +
                    '</tr>';
            });
            html += '</tbody></table></div>';

            if (d.tech) {
                html += '<div class="rb-muted" style="font-size:0.75rem; margin-top:0.5rem;">' +
                    'Narxi: ' + escapeHtml(String(d.tech.request_cost || 0)) + ' | Balans: ' + escapeHtml(String(d.tech.current_ballance || '?')) +
                    '</div>';
            }
            container.innerHTML = html;
        })
        .catch(function() {
            container.innerHTML = '<div class="rb-error-box">Xatolik yuz berdi</div>';
        });
});
