import re

with open('/Users/mac/GravityProjects/jaysonkhan_v2/backend/presentation/web/templates/web/partials/interactions.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace CSS
css_start = content.find('<style>')
css_end = content.find('</style>') + 8
new_css = """<style>
    /* ── Layout & Bubbles ── */
    .tg-bubble {
        background: #18222d;
        border-radius: 16px 16px 16px 4px; /* Consistent 16px radius */
        padding: 6px 10px 4px 12px;
        color: #fff;
        max-width: 75%; /* Mobile max-width */
        min-width: 80px;
        width: fit-content;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
        display: flex;
        flex-direction: column;
        transition: transform 0.2s, box-shadow 0.2s;
        word-break: break-word;
    }
    
    .tg-bubble.own-bubble {
        background: #2b5278; /* Sent bubble color */
        border-radius: 16px 16px 4px 16px; 
    }

    .comment-wrapper:hover .tg-bubble {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .tg-avatar {
        width: 38px !important;
        height: 38px !important;
        min-width: 38px;
        min-height: 38px;
        border-radius: 50% !important;
        object-fit: cover !important;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* ── Reply Preview ── */
    .tg-reply-preview {
        background: rgba(77, 163, 239, 0.08);
        border-left: 3px solid #4da3ef;
        padding: 4px 10px;
        margin-top: 4px;
        margin-bottom: 6px;
        border-radius: 4px 8px 8px 4px;
        font-size: 0.8rem;
        cursor: pointer;
        transition: background 0.2s;
        display: flex;
        flex-direction: column;
    }
    .tg-reply-preview:hover {
        background: rgba(77, 163, 239, 0.15);
    }
    .tg-reply-preview .author {
        color: #4da3ef;
        font-weight: 600;
        font-size: 0.75rem;
        margin-bottom: 2px;
    }
    .tg-reply-preview .text-snippet {
        color: rgba(255, 255, 255, 0.8);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* ── Images ── */
    .tg-comment-image {
        border-radius: 12px; /* Consistent image radius */
        margin-top: 6px;
        margin-bottom: 2px;
        max-width: 100%;
        display: block;
        cursor: pointer;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* ── Reactions ── */
    .tg-reaction-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 4px;
        padding-left: 4px;
    }
    .tg-reaction-btn {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px; /* Consistent pill radius */
        padding: 4px 10px;
        font-size: 0.75rem;
        color: #aeb7c2;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s ease;
        cursor: pointer;
        user-select: none;
    }
    .tg-reaction-btn:hover {
        background: rgba(255, 255, 255, 0.12);
    }
    .tg-reaction-btn.active {
        background: rgba(77, 163, 239, 0.15);
        border-color: rgba(77, 163, 239, 0.4);
        color: #4da3ef;
        font-weight: 600;
    }

    /* ── Typography & Meta ── */
    .tg-author-name {
        font-size: 0.8rem;
        font-weight: 600;
        color: #4da3ef;
        margin-bottom: 3px;
        display: block;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .tg-meta-inline {
        display: flex;
        align-items: flex-end;
        float: right;
        margin-left: 8px;
        margin-top: 4px;
        height: 100%;
        font-size: 0.65rem;
        line-height: 1;
        color: rgba(255, 255, 255, 0.4);
        user-select: none;
    }
    .tg-meta-inline-spacer {
        float: left;
        width: 38px; /* Spacer to push text so meta can fit bottom right */
        height: 10px;
    }

    /* ── Emoji Picker ── */
    .tg-emoji-menu {
        position: absolute;
        bottom: 120%;
        background: #1c2935;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 14px;
        padding: 8px;
        display: none;
        grid-template-columns: repeat(4, 1fr);
        gap: 6px;
        z-index: 100;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(10px);
    }
    .tg-emoji-menu.show { display: grid; }
    .tg-emoji-item {
        font-size: 1.4rem;
        cursor: pointer;
        padding: 6px;
        border-radius: 8px;
        transition: background 0.2s, transform 0.2s;
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .tg-emoji-item:hover {
        background: rgba(255, 255, 255, 0.1);
        transform: scale(1.15);
    }

    /* ── Reply Tooling ── */
    .tg-action-link {
        font-size: 0.75rem;
        color: #4da3ef;
        font-weight: 600;
        opacity: 0;
        transition: opacity 0.2s;
        cursor: pointer;
        margin-right: 8px;
    }
    .comment-wrapper:hover .tg-action-link { opacity: 0.8; }
    .tg-action-link:hover { opacity: 1 !important; text-decoration: underline; }
    
    @media (max-width: 640px) {
        .tg-bubble { max-width: 85%; }
        /* Shift emoji menu to fit screen */
        .tg-emoji-menu { right: 0; left: auto; }
    }
</style>"""

content = content[:css_start] + new_css + content[css_end:]

# Replace HTML loop logic
import re
html_regex = re.compile(r'({% for comment in comments %})(.*?)({% endfor %})', re.DOTALL)

def replace_html(m):
    return """{% for comment in comments %}
            <div class="flex gap-3 group comment-wrapper {% if tg_profile and comment.author.id == tg_profile.id %}flex-row-reverse{% endif %}" id="comment-{{ comment.id }}">
                {# Avatar #}
                <div class="flex-shrink-0 mt-1">
                    {% if comment.author.photo_url %}
                    <img src="{{ comment.author.photo_url }}" alt="{{ comment.author.display_name }}" class="tg-avatar">
                    {% else %}
                    <div class="tg-avatar bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-xs">
                        {{ comment.author.first_name|first|upper }}
                    </div>
                    {% endif %}
                </div>

                {# Bubble Container #}
                <div class="flex-1 min-w-0 flex flex-col {% if tg_profile and comment.author.id == tg_profile.id %}items-end{% else %}items-start{% endif %}">
                    <div class="tg-bubble {% if tg_profile and comment.author.id == tg_profile.id %}own-bubble{% endif %}">
                        {# Author Header (only show for others) #}
                        {% if not tg_profile or comment.author.id != tg_profile.id %}
                        <span class="tg-author-name">{{ comment.author.display_name }}</span>
                        {% endif %}

                        {# Reply Block #}
                        {% if comment.parent %}
                        <div class="tg-reply-preview" onclick="document.getElementById('comment-{{ comment.parent.id }}').scrollIntoView({behavior: 'smooth'})">
                            <span class="author">{{ comment.parent.author.display_name }}</span>
                            <span class="text-snippet">{{ comment.parent.text|truncatechars:80 }}</span>
                        </div>
                        {% endif %}

                        {# Image Attachment #}
                        {% if comment.image %}
                        <img src="{{ comment.image.url }}" class="tg-comment-image" alt="Attachment" onclick="window.open(this.src)">
                        {% endif %}

                        {# Content Text & Meta Data Layout #}
                        <div class="text-sm text-white/95 leading-relaxed relative">
                            {{ comment.text }}
                            <span class="tg-meta-inline-spacer"></span>
                            <span class="tg-meta-inline flex items-center gap-1">
                                {% if comment.is_reviewed %}
                                <i class="fa-solid fa-check-double text-[#4da3ef]"></i>
                                {% endif %}
                                {{ comment.created_at|date:"H:i" }}
                            </span>
                        </div>
                    </div>

                    {# Reactions List (Outside/Below Bubble) #}
                    <div class="tg-reaction-bar" id="reactions-{{ comment.id }}">
                        {% regroup comment.reactions.all by emoji as reaction_list %}
                        {% for group in reaction_list %}
                        <button
                            class="tg-reaction-btn {% for r in group.list %}{% if tg_profile and r.author.id == tg_profile.id %}active{% endif %}{% endfor %}"
                            onclick="toggleReaction({{ comment.id }}, '{{ group.grouper|escapejs }}', this)">
                            {{ group.grouper }} <span class="count">{{ group.list|length }}</span>
                        </button>
                        {% endfor %}

                        {# Plus Reaction / Reply Trigger #}
                        {% if tg_profile %}
                        <div class="flex items-center">
                            <div class="relative emoji-menu-wrapper">
                                <button
                                    class="tg-reaction-btn opacity-0 group-hover:opacity-100 transition-opacity ml-1"
                                    onclick="toggleEmojiMenu({{ comment.id }}, event)">
                                    <i class="fa-solid fa-face-smile text-[10px]"></i>
                                </button>
                                <div class="tg-emoji-menu" id="emoji-menu-{{ comment.id }}" {% if tg_profile and comment.author.id == tg_profile.id %}style="right: 0; left: auto;"{% else %}style="left: 0;"{% endif %}>
                                    <div class="tg-emoji-item" onclick="toggleReaction({{ comment.id }}, '👍')">👍</div>
                                    <div class="tg-emoji-item" onclick="toggleReaction({{ comment.id }}, '❤')">❤</div>
                                    <div class="tg-emoji-item" onclick="toggleReaction({{ comment.id }}, '🔥')">🔥</div>
                                    <div class="tg-emoji-item" onclick="toggleReaction({{ comment.id }}, '😂')">😂</div>
                                    <div class="tg-emoji-item" onclick="toggleReaction({{ comment.id }}, '👏')">👏</div>
                                    <div class="tg-emoji-item" onclick="toggleReaction({{ comment.id }}, '😱')">😱</div>
                                    <div class="tg-emoji-item" onclick="toggleReaction({{ comment.id }}, '👎')">👎</div>
                                    <div class="tg-emoji-item" onclick="toggleReaction({{ comment.id }}, '⚡')">⚡</div>
                                </div>
                            </div>
                            <span class="tg-action-link ml-2"
                                onclick="setReply({{ comment.id }}, '{{ comment.author.display_name|escapejs }}', '{{ comment.text|truncatechars:50|escapejs }}')">
                                Reply
                            </span>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}"""

content = html_regex.sub(replace_html, content)


js_regex = re.compile(r'(\(function \(\) \{)(.*?)(\}\)\(\);)', re.DOTALL)

def replace_js(m):
    return """(function () {
        let parentCommentId = null;
        let selectedFile = null;
        let reactionLocks = {}; // Per-comment locking to prevent duplicate reaction requests

        // ── Reply Logic ─────────────────────────────────────────────────────────
        window.setReply = function (id, name, snippet) {
            parentCommentId = id;
            document.getElementById('reply-author-name').textContent = name;
            document.getElementById('reply-text-preview').textContent = snippet;
            document.getElementById('reply-context').style.display = 'flex';
            document.getElementById('comment-text').focus();
            document.getElementById('comment-form-container').scrollIntoView({ behavior: 'smooth', block: 'end' });
        }

        window.clearReply = function () {
            parentCommentId = null;
            document.getElementById('reply-context').style.display = 'none';
        }

        // ── Image Preview ───────────────────────────────────────────────────────
        window.previewImage = function (input) {
            if (input.files && input.files[0]) {
                selectedFile = input.files[0];
                const reader = new FileReader();
                reader.onload = e => {
                    document.getElementById('image-preview').src = e.target.result;
                    document.getElementById('image-preview-container').style.display = 'block';
                };
                reader.readAsDataURL(selectedFile);
            }
        }

        window.clearImage = function () {
            selectedFile = null;
            document.getElementById('image-upload').value = '';
            document.getElementById('image-preview-container').style.display = 'none';
        }

        // ── Reactions ───────────────────────────────────────────────────────────
        window.toggleEmojiMenu = function (id, event) {
            event.stopPropagation();
            const menu = document.getElementById(`emoji-menu-${id}`);
            const allMenus = document.querySelectorAll('.tg-emoji-menu');
            allMenus.forEach(m => m !== menu && m.classList.remove('show'));
            menu.classList.toggle('show');
        }

        window.toggleReaction = async function (commentId, emoji, btnElem = null) {
            if (reactionLocks[commentId]) return;
            reactionLocks[commentId] = true;

            // Hide menus
            document.querySelectorAll('.tg-emoji-menu').forEach(m => m.classList.remove('show'));

            // Optimistic UI update could be implemented here (optional but complex)
            
            const url = `/interactions/comment/${commentId}/react/`;
            try {
                const resp = await fetch(url, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' },
                    body: JSON.stringify({ emoji })
                });

                if (resp.status === 401) {
                    alert("Please login with Telegram to react.");
                    reactionLocks[commentId] = false;
                    return;
                }

                const data = await resp.json();
                if (resp.ok && data.status === 'ok') {
                    updateReactionDOM(commentId, data.reactions, data.action, emoji);
                }
            } catch (e) {
                console.error("Reaction failed", e);
            } finally {
                reactionLocks[commentId] = false;
            }
        }

        function updateReactionDOM(commentId, reactions, action, currentEmoji) {
            const container = document.getElementById(`reactions-${commentId}`);
            if (!container) return;

            const triggerEl = container.querySelector('.flex.items-center');
            
            // Remove all existing reaction buttons
            const reactionBtns = container.querySelectorAll('.tg-reaction-btn:not(.opacity-0)');
            reactionBtns.forEach(btn => btn.remove());

            // Add new buttons based on backend state
            Object.entries(reactions).forEach(([emoji, count]) => {
                const btn = document.createElement('button');
                btn.className = 'tg-reaction-btn';
                
                // If this is the emoji the user just acted upon and it was an 'added' or 'updated' action, mark active
                // For proper tracking across page reloads, server should return user's active emoji. 
                // We fake it optimistically here: if it's the one we just clicked, and it wasn't removed.
                if (emoji === currentEmoji && action !== 'removed') {
                    btn.classList.add('active');
                }
                
                btn.onclick = () => window.toggleReaction(commentId, emoji);
                btn.innerHTML = `${emoji} <span class="count">${count}</span>`;
                container.insertBefore(btn, triggerEl);
            });
        }

        // ── Form Submission (Multipart) ──────────────────────────────────────────
        const submitBtn = document.getElementById('submit-comment');
        if (submitBtn) {
            submitBtn.addEventListener('click', async () => {
                const text = (document.getElementById('comment-text').value || '').trim();
                if (!text && !selectedFile) { alert("Comment cannot be empty"); return; }

                submitBtn.disabled = true;
                const originalContent = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-sm"></i>';

                const formData = new FormData();
                formData.append('text', text);
                if (parentCommentId) formData.append('parent_id', parentCommentId);
                if (selectedFile) formData.append('image', selectedFile);

                try {
                    const resp = await fetch(submitBtn.dataset.url, {
                        method: 'POST',
                        headers: { 'X-CSRFToken': getCookie('csrftoken') },
                        body: formData
                    });
                    const data = await resp.json();
                    if (resp.status === 201) {
                        location.reload();
                    } else {
                        alert(data.error || "Error sending comment");
                    }
                } catch (e) {
                    alert("Network error");
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalContent;
                }
            });
        }

        // ── Global Clicks ────────────────────────────────────────────────────────
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.emoji-menu-wrapper')) {
                document.querySelectorAll('.tg-emoji-menu').forEach(m => m.classList.remove('show'));
            }
        });

        // ── Helpers ─────────────────────────────────────────────────────────────
        function getCookie(name) {
            const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
            return m ? m.pop() : '';
        }
    })();"""

content = js_regex.sub(replace_js, content)

with open('/Users/mac/GravityProjects/jaysonkhan_v2/backend/presentation/web/templates/web/partials/interactions.html', 'w', encoding='utf-8') as f:
    f.write(content)

