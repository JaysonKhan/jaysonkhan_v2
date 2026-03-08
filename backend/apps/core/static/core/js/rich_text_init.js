/**
 * TinyMCE 6 — Rich text editor init for Django admin.
 * Self-hosted via cdnjs — no API key required.
 * Dark oxide skin matches the Unfold admin dark theme.
 */

(function () {
    'use strict';

    // ── Helpers ──────────────────────────────────────────────────────────────

    function getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (const c of cookies) {
            const trimmed = c.trim();
            if (trimmed.startsWith('csrftoken=')) {
                return trimmed.slice('csrftoken='.length);
            }
        }
        return '';
    }

    /** Upload handler: POST to /api/admin/media-upload/ with CSRF header. */
    function imagesUploadHandler(blobInfo, progress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.withCredentials = false;
            xhr.open('POST', '/api/admin/media-upload/');

            const csrf = getCsrfToken();
            if (csrf) xhr.setRequestHeader('X-CSRFToken', csrf);

            xhr.upload.onprogress = function (e) {
                if (e.lengthComputable) progress((e.loaded / e.total) * 100);
            };

            xhr.onload = function () {
                if (xhr.status === 403) {
                    reject({ message: 'Upload forbidden (403). Check CSRF token.', remove: true });
                    return;
                }
                if (xhr.status < 200 || xhr.status >= 300) {
                    reject('Upload failed: HTTP ' + xhr.status);
                    return;
                }
                var json;
                try { json = JSON.parse(xhr.responseText); } catch (e) {
                    reject('Invalid JSON response from upload endpoint.');
                    return;
                }
                if (!json || typeof json.location !== 'string') {
                    reject('Upload response missing "location" field.');
                    return;
                }
                resolve(json.location);
            };

            xhr.onerror = function () {
                reject('Network error during upload (XHR transport).');
            };

            var form = new FormData();
            form.append('file', blobInfo.blob(), blobInfo.filename());
            xhr.send(form);
        });
    }

    // ── TinyMCE config ───────────────────────────────────────────────────────

    var TINYMCE_CONFIG = {
        selector: 'textarea.rich-text-editor',

        // Dark skin — matches Unfold dark admin theme
        skin: 'oxide-dark',
        content_css: 'dark',

        // Plugins (all included in TinyMCE 6 open-source cdnjs bundle)
        plugins: 'advlist autolink lists link image charmap preview anchor searchreplace wordcount visualblocks code fullscreen insertdatetime media table emoticons codesample',

        // Toolbar — grouped by function
        toolbar: 'undo redo | blocks | bold italic underline strikethrough | forecolor backcolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image media codesample blockquote | table emoticons charmap | searchreplace wordcount | code preview fullscreen',

        toolbar_mode: 'sliding',
        toolbar_sticky: true,

        height: 640,
        min_height: 400,

        block_formats: 'Paragraph=p; Heading 1=h1; Heading 2=h2; Heading 3=h3; Heading 4=h4; Preformatted=pre',

        // Image upload
        image_title: true,
        automatic_uploads: true,
        images_upload_url: '/api/admin/media-upload/',
        images_upload_handler: imagesUploadHandler,
        file_picker_types: 'image media',
        media_live_embeds: true,

        // Code sample languages
        codesample_languages: [
            { text: 'Dart / Flutter', value: 'dart' },
            { text: 'Python',         value: 'python' },
            { text: 'JavaScript',     value: 'javascript' },
            { text: 'TypeScript',     value: 'typescript' },
            { text: 'HTML/XML',       value: 'markup' },
            { text: 'CSS',            value: 'css' },
            { text: 'JSON',           value: 'json' },
            { text: 'Bash',           value: 'bash' },
            { text: 'SQL',            value: 'sql' },
            { text: 'Kotlin',         value: 'kotlin' },
            { text: 'Swift',          value: 'swift' }
        ],

        // Preview content styles — dark, matches site design
        content_style: [
            'body {',
            '  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;',
            '  font-size: 16px; line-height: 1.85;',
            '  color: #cbd5e1; background: #0f172a;',
            '  padding: 1.5rem 2rem; max-width: 740px; margin: 0 auto;',
            '}',
            'h1,h2,h3,h4,h5,h6 { color:#f1f5f9; font-weight:700; line-height:1.3; margin-top:2rem; margin-bottom:.6rem; }',
            'h1{font-size:2rem;} h2{font-size:1.6rem;} h3{font-size:1.3rem;} h4{font-size:1.1rem;}',
            'p { margin:0 0 1.2rem; }',
            'a { color:#818cf8; text-decoration:underline; }',
            'strong,b { color:#e2e8f0; font-weight:700; }',
            'em,i { font-style:italic; }',
            'img { max-width:100%; height:auto; border-radius:8px; margin:1.5rem auto; display:block; border:1px solid rgba(255,255,255,.08); box-shadow:0 4px 20px rgba(0,0,0,.4); }',
            'iframe { width:100%; aspect-ratio:16/9; height:auto; border-radius:8px; margin:1.5rem 0; border:1px solid rgba(255,255,255,.08); }',
            'blockquote { border-left:3px solid #818cf8; background:rgba(99,102,241,.07); padding:.9rem 1.2rem; border-radius:0 8px 8px 0; margin:1.5rem 0; color:#94a3b8; font-style:italic; }',
            'blockquote p { margin-bottom:0; }',
            'pre { background:rgba(15,23,42,.9); border:1px solid rgba(99,102,241,.2); border-radius:8px; padding:1rem 1.25rem; overflow-x:auto; font-family:monospace; font-size:.88rem; color:#94a3b8; margin:1.25rem 0; }',
            'code { font-family:monospace; font-size:.875em; background:rgba(99,102,241,.12); color:#a5b4fc; border:1px solid rgba(99,102,241,.2); border-radius:4px; padding:.15em .4em; }',
            'ul,ol { padding-left:1.5rem; margin:.75rem 0 1rem; }',
            'li { margin-bottom:.35rem; }',
            'hr { border:none; height:1px; background:rgba(99,102,241,.2); margin:2rem 0; }',
            'table { width:100%; border-collapse:collapse; margin:1.25rem 0; }',
            'th { background:rgba(99,102,241,.1); color:#e2e8f0; font-weight:600; padding:.6rem .9rem; text-align:left; border:1px solid rgba(255,255,255,.08); }',
            'td { padding:.55rem .9rem; border:1px solid rgba(255,255,255,.06); color:#cbd5e1; }',
            'tr:nth-child(even) td { background:rgba(255,255,255,.02); }'
        ].join('\n'),

        branding: false,
        promotion: false,
        resize: true,
        statusbar: true,
        elementpath: false,
        paste_data_images: true,

        setup: function (editor) {
            // Sync to textarea on every change so Django form captures the value
            editor.on('change input keyup', function () {
                editor.save();
            });
        }
    };

    // ── Init & reinit logic ──────────────────────────────────────────────────

    function initEditors() {
        if (typeof tinymce === 'undefined') return;
        var textareas = document.querySelectorAll('textarea.rich-text-editor');
        textareas.forEach(function (el) {
            // Skip if already initialized for this element
            if (!tinymce.get(el.id || el.name)) {
                var cfg = Object.assign({}, TINYMCE_CONFIG);
                cfg.target = el;
                delete cfg.selector;
                tinymce.init(cfg);
            }
        });
    }

    function waitForTinyMCE(cb, tries) {
        tries = tries || 0;
        if (typeof tinymce !== 'undefined') { cb(); return; }
        if (tries > 60) { console.warn('[RichText] TinyMCE did not load in time.'); return; }
        setTimeout(function () { waitForTinyMCE(cb, tries + 1); }, 100);
    }

    document.addEventListener('DOMContentLoaded', function () {
        waitForTinyMCE(initEditors);

        // Reinitialize when Unfold admin reveals a tab that was hidden on load
        var observer = new MutationObserver(function () {
            var pending = document.querySelectorAll('textarea.rich-text-editor');
            if (pending.length) waitForTinyMCE(initEditors);
        });
        observer.observe(document.body, { childList: true, subtree: true });
    });
})();
