/**
 * OSINT Core — shared utility functions + UI components
 * Used by: osint-profile.js, osint-entity.js, osint-search.js
 */

/* ── XSS-safe HTML escaping ──────────────────────────────────────── */

function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

/**
 * Sanitize HTML — faqat xavfsiz Telegram formatlash teglarini qoldirish.
 * Ruxsat: <b>, <i>, <u>, <s>, <code>, <pre>, <a href="...">, <br>
 * Boshqa hamma teglar olib tashlanadi (XSS himoya).
 */
function sanitizeHtml(html) {
    if (!html) return '';
    var tmp = document.createElement('div');
    tmp.innerHTML = html;

    function cleanNode(parent) {
        var children = Array.prototype.slice.call(parent.childNodes);
        for (var i = 0; i < children.length; i++) {
            var node = children[i];
            if (node.nodeType === 3) continue; // text node — safe
            if (node.nodeType !== 1) { node.remove(); continue; } // comment etc

            var tag = node.tagName.toLowerCase();
            var allowed = ['b', 'strong', 'i', 'em', 'u', 's', 'del', 'code', 'pre', 'a', 'br', 'span'];
            if (allowed.indexOf(tag) === -1) {
                // Ruxsat berilmagan teg — faqat textContent qoldirish
                var text = document.createTextNode(node.textContent || '');
                parent.replaceChild(text, node);
                continue;
            }
            // <a> tegida faqat href qoldirish, boshqa attributelarni olib tashlash
            if (tag === 'a') {
                var href = node.getAttribute('href') || '';
                // faqat http/https/tg linklar ruxsat
                if (!/^(https?:|tg:)/i.test(href)) href = '#';
                // barcha attributelarni olib tashlash
                while (node.attributes.length > 0) node.removeAttribute(node.attributes[0].name);
                node.setAttribute('href', href);
                node.setAttribute('target', '_blank');
                node.setAttribute('rel', 'noopener noreferrer');
            } else {
                // boshqa teglarda barcha attributelarni olib tashlash
                while (node.attributes.length > 0) node.removeAttribute(node.attributes[0].name);
            }
            cleanNode(node);
        }
    }
    cleanNode(tmp);
    return tmp.innerHTML;
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

/* ── ConfirmDialog — reusable modal ──────────────────────────────── */

var ConfirmDialog = {
    _overlay: null,

    /**
     * Show confirmation dialog.
     * @param {Object} opts - { title, message, balance, confirmText, cancelText }
     * @returns {Promise<boolean>}
     */
    show: function(opts) {
        var self = this;
        return new Promise(function(resolve) {
            // Remove existing
            self.hide();

            var overlay = document.createElement('div');
            overlay.className = 'rb-confirm-overlay';
            overlay.setAttribute('role', 'dialog');
            overlay.setAttribute('aria-modal', 'true');
            overlay.setAttribute('aria-label', opts.title || 'Tasdiqlash');

            var dialog = document.createElement('div');
            dialog.className = 'rb-confirm-dialog';

            // Icon
            var iconDiv = document.createElement('div');
            iconDiv.className = 'rb-confirm-icon';
            iconDiv.innerHTML = '<span class="material-symbols-outlined">warning</span>';
            dialog.appendChild(iconDiv);

            // Title
            var title = document.createElement('h3');
            title.className = 'rb-confirm-title';
            title.textContent = opts.title || 'Tasdiqlash';
            dialog.appendChild(title);

            // Message
            var msg = document.createElement('div');
            msg.className = 'rb-confirm-message';
            msg.innerHTML = opts.message || '';
            dialog.appendChild(msg);

            // Balance display
            if (opts.balance != null) {
                var bal = document.createElement('div');
                bal.className = 'rb-confirm-balance';
                bal.innerHTML = '<span class="material-symbols-outlined" style="font-size:14px;">account_balance_wallet</span> ' +
                    'Balans: <strong>' + parseFloat(opts.balance).toFixed(0) + '</strong> kredit';
                dialog.appendChild(bal);
            }

            // Buttons
            var btns = document.createElement('div');
            btns.className = 'rb-confirm-actions';

            var confirmBtn = document.createElement('button');
            confirmBtn.className = 'rb-btn rb-btn-primary';
            confirmBtn.innerHTML = '<span class="material-symbols-outlined" style="font-size:16px;">check</span> ' +
                (opts.confirmText || 'Davom etish');
            confirmBtn.addEventListener('click', function() { self.hide(); resolve(true); });

            var cancelBtn = document.createElement('button');
            cancelBtn.className = 'rb-btn rb-btn-outline';
            cancelBtn.textContent = opts.cancelText || 'Bekor qilish';
            cancelBtn.addEventListener('click', function() { self.hide(); resolve(false); });

            btns.appendChild(confirmBtn);
            btns.appendChild(cancelBtn);
            dialog.appendChild(btns);

            overlay.appendChild(dialog);
            document.body.appendChild(overlay);
            self._overlay = overlay;

            // Focus trap
            confirmBtn.focus();

            // ESC to cancel
            var escHandler = function(e) {
                if (e.key === 'Escape') {
                    document.removeEventListener('keydown', escHandler);
                    self.hide();
                    resolve(false);
                }
            };
            document.addEventListener('keydown', escHandler);

            // Click outside to cancel
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) {
                    document.removeEventListener('keydown', escHandler);
                    self.hide();
                    resolve(false);
                }
            });
        });
    },

    hide: function() {
        if (this._overlay) {
            this._overlay.remove();
            this._overlay = null;
        }
    }
};

/* ── ErrorCard — structured error display ────────────────────────── */

var ERROR_TYPES = {
    401: { icon: 'key_off',    title: 'Autentifikatsiya xatosi', detail: 'Token muddati o\'tgan bo\'lishi mumkin.', retryable: false },
    403: { icon: 'lock',       title: 'Ruxsat berilmagan',       detail: 'Bu ma\'lumotga kirish huquqi yo\'q.', retryable: false },
    404: { icon: 'search_off', title: 'Ma\'lumot topilmadi',     detail: 'So\'ralgan ma\'lumot mavjud emas.',    retryable: false },
    429: { icon: 'speed',      title: 'Limit oshdi',             detail: 'So\'rovlar limiti oshib ketdi. Biroz kuting.', retryable: true },
    500: { icon: 'error',      title: 'Server xatosi',           detail: 'Ichki server xatosi yuz berdi.',       retryable: true },
    502: { icon: 'cloud_off',  title: 'Server javob bermayapti', detail: 'Tashqi server vaqtinchalik ishlamayapti.', retryable: true },
    503: { icon: 'cloud_off',  title: 'Xizmat mavjud emas',     detail: 'Server vaqtinchalik ishlamayapti.',    retryable: true },
    504: { icon: 'timer_off',  title: 'Vaqt tugadi',             detail: 'Server javob berish vaqti oshib ketdi.', retryable: true },
    0:   { icon: 'wifi_off',   title: 'Ulanish xatosi',         detail: 'Tarmoq bilan bog\'lanish yo\'q.',       retryable: true }
};

/**
 * Build error card HTML.
 * @param {string} errorMsg - Error message text
 * @param {Function} [retryFn] - Optional retry callback name as string (for onclick)
 * @returns {string} HTML string
 */
function buildErrorCard(errorMsg, retryFn) {
    // Detect error code from message
    var errInfo = null;
    var codes = Object.keys(ERROR_TYPES);
    for (var i = 0; i < codes.length; i++) {
        if (errorMsg.indexOf(codes[i]) !== -1) {
            errInfo = ERROR_TYPES[codes[i]];
            break;
        }
    }
    if (!errInfo) errInfo = { icon: 'error', title: 'Xatolik', detail: errorMsg, retryable: !!retryFn };

    var html = '<div class="rb-error-card">' +
        '<div class="rb-error-card-icon"><span class="material-symbols-outlined">' + errInfo.icon + '</span></div>' +
        '<div class="rb-error-card-content">' +
            '<div class="rb-error-card-title">' + errInfo.title + '</div>' +
            '<div class="rb-error-card-detail">' + escapeHtml(errInfo.detail || errorMsg) + '</div>' +
        '</div>';

    if (errInfo.retryable && retryFn) {
        html += '<button class="rb-btn rb-btn-outline rb-btn-sm" onclick="' + retryFn + '">' +
            '<span class="material-symbols-outlined" style="font-size:14px;">refresh</span> Qayta urinish</button>';
    }
    html += '</div>';
    return html;
}
