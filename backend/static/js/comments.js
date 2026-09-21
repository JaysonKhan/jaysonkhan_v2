/* Shared discussion UI. Server supplies localized copy, URLs and the first page. */
(function () {
  'use strict';
  const panel = document.getElementById('comments-section');
  if (!panel) return;
  const $ = id => document.getElementById('discussion-' + id);
  const labels = JSON.parse($('labels').textContent);
  const limits = JSON.parse($('limits').textContent);
  const initial = JSON.parse($('data').textContent);
  const lang = document.documentElement.lang || 'xo';
  const loggedIn = !!panel.dataset.user;
  const comments = new Map();
  const threads = new Map();
  let sort = 'top', page = initial.page, hasNext = initial.has_next;
  let generation = 0, loading = false, controller;
  let parentId = null, replyTarget = null, selectedFile = null, previewURL = null, sending = false;
  let lastReplyButton = null;
  const draftKey = `jk-comment:${panel.dataset.user}:${panel.dataset.app}:${panel.dataset.model}:${panel.dataset.oid}`;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function button(text, className, action) {
    const node = el('button', className, text);
    node.type = 'button'; node.addEventListener('click', action); return node;
  }
  function status(message, error = false) {
    $('status').textContent = message; $('status').hidden = !message;
    $('status').classList.toggle('is-error', error);
  }
  function goTo(node) {
    node.focus({preventScroll: true});
    window.scrollTo({top: scrollY + node.getBoundingClientRect().top - 120, behavior: reduced ? 'auto' : 'smooth'});
  }
  function requireLogin() {
    status(labels.login);
    const login = $('login');
    if (login) goTo(login);
  }
  async function request(url, options = {}) {
    let response;
    try { response = await fetch(url, {...options, credentials: 'same-origin', headers: {'Accept-Language': lang, ...options.headers}}); }
    catch (error) { if (error.name === 'AbortError') throw error; throw new Error(labels.networkError); }
    let data;
    try { data = await response.json(); } catch (_) { throw new Error(labels.genericError); }
    if (!response.ok) {
      if (response.status === 401) requireLogin();
      throw new Error(data.error || labels.genericError);
    }
    return data;
  }
  function urlFor(template, id) { return template.replace('/0/', `/${id}/`); }
  function listURL(extra = {}) {
    const url = new URL(panel.dataset.listUrl, location.href);
    url.search = new URLSearchParams({app_label: panel.dataset.app, model: panel.dataset.model, object_id: panel.dataset.oid, sort, ...extra});
    return url;
  }
  function safeURL(value) {
    try { const url = new URL(value, location.href); return ['http:', 'https:'].includes(url.protocol) ? url.href : ''; }
    catch (_) { return ''; }
  }
  function formatDate(value) {
    const date = new Date(value);
    try { return new Intl.DateTimeFormat(lang === 'xo' ? 'uz' : lang, {day: 'numeric', month: ['xo', 'uz'].includes(lang) ? '2-digit' : 'short', year: 'numeric'}).format(date); }
    catch (_) { return value.slice(0, 10); }
  }
  function renderReactions(comment, bar) {
    bar.replaceChildren();
    Object.entries(comment.reaction_counts || {}).forEach(([emoji, count]) => {
      const chip = button(emoji + ' ', 'discussion-reaction', () => react(comment, emoji, bar));
      chip.append(el('span', '', count)); chip.setAttribute('aria-pressed', String(comment.user_reaction === emoji));
      chip.setAttribute('aria-label', `${labels.react}: ${emoji} · ${count}`); bar.append(chip);
    });
    if (loggedIn) {
      const picker = el('details', 'discussion-picker');
      const summary = el('summary', 'discussion-text-btn', labels.react);
      const menu = el('div', 'discussion-emojis');
      ['👍', '❤', '🔥', '😂', '👏', '😱', '👎', '⚡'].forEach(emoji => {
        const item = button(emoji, '', () => { picker.open = false; summary.focus(); react(comment, emoji, bar); });
        item.setAttribute('aria-label', `${labels.react}: ${emoji}`); menu.append(item);
      });
      picker.addEventListener('toggle', () => {
        if (picker.open) {
          panel.querySelectorAll('.discussion-picker[open]').forEach(other => { if (other !== picker) other.open = false; });
          menu.style.left = '0px';
          const rect = menu.getBoundingClientRect();
          if (rect.right > innerWidth - 16) menu.style.left = `${innerWidth - 16 - rect.right}px`;
          const adjusted = menu.getBoundingClientRect();
          if (adjusted.left < 16) menu.style.left = `${parseFloat(menu.style.left) + 16 - adjusted.left}px`;
        }
      });
      picker.append(summary, menu); bar.append(picker);
    } else bar.append(button(labels.react, 'discussion-text-btn', requireLogin));
    if (!comment.parent_id) bar.append(button(labels.reply, 'discussion-text-btn', event => {
      if (!loggedIn) return requireLogin();
      parentId = comment.id; replyTarget = comment; lastReplyButton = event.currentTarget;
      $('reply-name').textContent = labels.replyingTo.replace('{name}', comment.author.display_name);
      $('reply-preview').textContent = comment.text || labels.image;
      $('reply-context').hidden = false; saveDraft(); goTo($('text'));
    }));
  }
  async function react(comment, emoji, bar) {
    if (!loggedIn) return requireLogin();
    if (comment.busy) return;
    comment.busy = true; bar.setAttribute('aria-busy', 'true');
    try {
      const data = await request(urlFor(panel.dataset.reactUrl, comment.id), {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({emoji})});
      comment.reaction_counts = data.reactions; comment.user_reaction = data.user_reaction;
      renderReactions(comment, bar);
      const focus = bar.querySelector('[aria-pressed=true]') || bar.querySelector('summary');
      if (focus) focus.focus({preventScroll: true});
    } catch (error) { status(error.message, true); }
    finally { comment.busy = false; bar.removeAttribute('aria-busy'); }
  }
  function createComment(comment) {
    comments.set(comment.id, comment);
    const row = el('article', 'discussion-comment'); row.id = `comment-${comment.id}`; row.tabIndex = -1; row.dataset.createdAt = comment.created_at;
    const avatar = el('div', 'discussion-avatar', comment.author.initial);
    if (comment.author.photo_url && safeURL(comment.author.photo_url)) {
      const img = el('img'); img.src = safeURL(comment.author.photo_url); img.alt = ''; img.loading = 'lazy'; img.referrerPolicy = 'no-referrer';
      img.addEventListener('error', () => { avatar.textContent = comment.author.initial; }, {once: true}); avatar.replaceChildren(img);
    }
    const body = el('div', 'discussion-comment-body');
    const header = el('header'); header.append(el('strong', '', comment.author.display_name));
    if (comment.is_own) header.append(el('span', 'discussion-you', labels.you));
    const permalink = el('a', 'discussion-time'); permalink.href = `#comment-${comment.id}`; permalink.title = labels.link;
    const time = el('time', '', formatDate(comment.created_at)); time.dateTime = comment.created_at; permalink.append(time); header.append(permalink); body.append(header);
    if (comment.text) body.append(el('p', 'discussion-text', comment.text));
    if (comment.image_url && safeURL(comment.image_url)) {
      const link = el('a', 'discussion-image lightbox-trigger'); link.href = safeURL(comment.image_url);
      link.dataset.lightbox = ''; link.dataset.full = link.href; link.dataset.hint = `${labels.image} · ${comment.author.display_name}`; link.dataset.closeLabel = labels.close;
      const image = el('img'); image.src = link.href; image.alt = labels.image; image.loading = 'lazy';
      link.append(image, el('span', 'discussion-image-caption', labels.image + ' ↗')); body.append(link);
    }
    const actions = el('div', 'discussion-actions'); renderReactions(comment, actions); body.append(actions);
    if (!comment.parent_id) {
      const toggle = button(`${labels.replies} · ${comment.reply_count}`, 'discussion-text-btn discussion-thread-toggle', () => toggleThread(comment.id));
      toggle.setAttribute('aria-expanded', 'false'); toggle.setAttribute('aria-controls', `replies-${comment.id}`); toggle.hidden = !comment.reply_count;
      const replies = el('div', 'discussion-replies'); replies.id = `replies-${comment.id}`; replies.hidden = true;
      const list = el('div'); const earlier = button(labels.earlierReplies, 'discussion-text-btn', () => loadReplies(comment.id, null, true)); earlier.hidden = true; const more = button(labels.moreReplies, 'discussion-text-btn', () => loadReplies(comment.id)); more.hidden = true;
      replies.append(earlier, list, more); body.append(toggle, replies);
      threads.set(comment.id, {toggle, replies, list, more, earlier, firstPage: 1, page: 0, loaded: false, busy: false, count: comment.reply_count});
    }
    row.append(avatar, body); return row;
  }
  function addComment(comment, target, prepend = false) {
    if (document.getElementById(`comment-${comment.id}`)) return;
    const row = createComment(comment);
    if (comment.parent_id) {
      const next = Array.from(target.children).find(item => item.dataset.createdAt > comment.created_at ||
        (item.dataset.createdAt === comment.created_at && Number(item.id.replace('comment-', '')) > comment.id));
      target.insertBefore(row, next || null);
    } else prepend ? target.prepend(row) : target.append(row);
  }
  async function toggleThread(id) {
    const thread = threads.get(id); thread.replies.hidden = !thread.replies.hidden;
    thread.toggle.setAttribute('aria-expanded', String(!thread.replies.hidden));
    thread.toggle.textContent = thread.replies.hidden ? `${labels.replies} · ${thread.count}` : labels.hideReplies;
    if (!thread.replies.hidden && !thread.loaded) await loadReplies(id);
  }
  async function loadReplies(id, focus = null, previous = false) {
    const thread = threads.get(id);
    if (thread.busy) return;
    thread.busy = true; const control = previous ? thread.earlier : thread.more;
    control.hidden = false; control.textContent = labels.loading; thread.more.disabled = true; thread.earlier.disabled = true;
    const url = new URL(urlFor(panel.dataset.repliesUrl, id), location.href);
    url.search = new URLSearchParams(focus ? {focus} : {page: previous ? thread.firstPage - 1 : thread.page + 1});
    try {
      const data = await request(url);
      if (!thread.replies.isConnected) return;
      const replies = previous ? data.replies.slice().reverse() : data.replies;
      replies.forEach(reply => addComment(reply, thread.list, previous));
      if (!thread.loaded || previous) thread.firstPage = data.page;
      if (!previous) { thread.page = data.page; thread.more.hidden = !data.has_next; }
      thread.loaded = true; thread.count = data.total_count; thread.earlier.hidden = thread.firstPage <= 1;
      control.textContent = previous ? labels.earlierReplies : labels.moreReplies;
      if (focus) { const node = document.getElementById(`comment-${focus}`); if (node) goTo(node); }
    } catch (error) { control.textContent = labels.retry; status(error.message, true); }
    finally { thread.busy = false; thread.more.disabled = false; thread.earlier.disabled = false; }
  }
  function renderPage(data, reset) {
    if (reset) { $('list').replaceChildren(); comments.clear(); threads.clear(); }
    data.comments.forEach(comment => addComment(comment, $('list')));
    if (!$('list').children.length) $('list').append(el('p', 'discussion-empty', labels.empty));
    $('count').textContent = data.discussion_count;
    page = data.page; hasNext = data.has_next; $('more').hidden = !hasNext;
  }
  async function loadComments(reset = false) {
    if (loading && !reset) return;
    if (controller) controller.abort(); controller = new AbortController();
    const seq = ++generation; loading = true;
    $('list').setAttribute('aria-busy', 'true'); $('more').disabled = true; $('more').textContent = labels.loading; $('load-error').hidden = true;
    try {
      const data = await request(listURL({page: reset ? 1 : page + 1}), {signal: controller.signal});
      if (seq !== generation) return;
      renderPage(data, reset);
    } catch (error) { if (error.name !== 'AbortError' && seq === generation) { $('load-error').hidden = false; $('retry').onclick = () => loadComments(reset); } }
    finally { if (seq === generation) { loading = false; $('list').removeAttribute('aria-busy'); $('more').disabled = false; $('more').textContent = labels.moreComments; } }
  }
  panel.querySelectorAll('[data-enhanced]').forEach(node => { node.hidden = false; });
  renderPage(initial, true);
  $('more').addEventListener('click', () => loadComments());
  panel.querySelectorAll('[data-sort]').forEach(node => node.addEventListener('click', () => {
    sort = node.dataset.sort;
    panel.querySelectorAll('[data-sort]').forEach(item => item.setAttribute('aria-pressed', String(item === node)));
    loadComments(true);
  }));
  $('like').addEventListener('click', async () => {
    if (!loggedIn) return requireLogin();
    const node = $('like'); if (node.disabled) return; node.disabled = true;
    try {
      const data = await request(panel.dataset.likeUrl, {method: 'POST'});
      $('like-count').textContent = data.count; node.setAttribute('aria-pressed', String(data.liked)); node.setAttribute('aria-label', `${labels.likes}: ${data.count}`);
    } catch (error) { status(error.message, true); }
    finally { node.disabled = false; }
  });
  function formError(message) { $('form-error').textContent = message; $('form-error').hidden = !message; }
  function updateInput() {
    const text = $('text').value; const count = Array.from(text).length;
    $('chars').textContent = `${count} / ${limits.maxLength}`;
    $('send').disabled = sending || count > limits.maxLength || (text.trim().length < limits.minLength && !selectedFile);
  }
  function saveDraft() {
    try { sessionStorage.setItem(draftKey, JSON.stringify({text: $('text').value, time: Date.now()})); } catch (_) { /* Storage may be disabled. */ }
  }
  function clearReply(restoreFocus = false) {
    parentId = null; replyTarget = null; $('reply-context').hidden = true;
    if (restoreFocus && lastReplyButton && lastReplyButton.isConnected) lastReplyButton.focus();
  }
  function clearImage() {
    if (previewURL) URL.revokeObjectURL(previewURL); previewURL = null; selectedFile = null;
    $('image').value = ''; $('preview-image').removeAttribute('src'); $('preview').hidden = true; updateInput();
  }
  if (loggedIn) {
    try {
      const draft = JSON.parse(sessionStorage.getItem(draftKey));
      if (draft && Date.now() - draft.time < 86400000 && draft.text) { $('text').value = draft.text; status(labels.draftRestored); }
    } catch (_) { /* No draft. */ }
    updateInput();
    $('text').addEventListener('input', () => { updateInput(); formError(''); saveDraft(); });
    $('text').addEventListener('keydown', event => {
      if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.isComposing) { event.preventDefault(); if (!$('send').disabled) $('form').requestSubmit(); }
    });
    $('cancel-reply').addEventListener('click', () => clearReply(true));
    $('remove-image').addEventListener('click', () => { clearImage(); $('image').focus(); });
    $('image').addEventListener('change', () => {
      const file = $('image').files[0]; if (!file) return;
      if (!['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type) || file.size > limits.maxImageMB * 1024 * 1024) {
        clearImage(); formError(labels.imageHint.replace('{n}', limits.maxImageMB)); return;
      }
      if (previewURL) URL.revokeObjectURL(previewURL);
      selectedFile = file; previewURL = URL.createObjectURL(file); $('preview-image').src = previewURL;
      $('file-name').textContent = file.name; $('preview').hidden = false; formError(''); updateInput();
    });
    $('form').addEventListener('submit', async event => {
      event.preventDefault(); if (sending) return;
      const text = $('text').value.trim();
      if (Array.from(text).length > limits.maxLength) return formError(labels.maxChars.replace('{n}', limits.maxLength));
      if (text.length < limits.minLength && !selectedFile) return formError(labels.minChars.replace('{n}', limits.minLength));
      const body = new FormData(); body.append('text', text); if (parentId) body.append('parent_id', parentId); if (selectedFile) body.append('image', selectedFile);
      const submittedParent = replyTarget;
      if (controller) controller.abort(); ++generation; loading = false; $('list').removeAttribute('aria-busy'); $('more').textContent = labels.moreComments;
      panel.querySelectorAll('[data-sort], #discussion-more').forEach(node => { node.disabled = true; });
      sending = true; $('form').querySelector('fieldset').disabled = true; $('send').textContent = labels.sending; formError('');
      try {
        const data = await request($('form').action, {method: 'POST', body});
        $('text').value = ''; saveDraft(); clearImage(); clearReply(); status(data.message);
        if (data.comment) {
          const c = data.comment; $('list').querySelector('.discussion-empty')?.remove();
          if (c.parent_id && !threads.has(c.parent_id) && submittedParent) addComment(submittedParent, $('list'), true);
          if (c.parent_id && threads.has(c.parent_id)) {
            const thread = threads.get(c.parent_id); thread.replies.hidden = false; thread.toggle.hidden = false;
            thread.toggle.textContent = labels.hideReplies; thread.toggle.setAttribute('aria-expanded', 'true');
            if (!thread.loaded) await loadReplies(c.parent_id);
            else thread.count += 1;
            addComment(c, thread.list);
          } else addComment(c, $('list'), true);
          $('count').textContent = Number($('count').textContent) + 1;
          const node = document.getElementById(`comment-${c.id}`); if (node) goTo(node);
        }
      } catch (error) { formError(error.message); }
      finally { panel.querySelectorAll('[data-sort], #discussion-more').forEach(node => { node.disabled = false; }); sending = false; $('form').querySelector('fieldset').disabled = false; $('send').textContent = labels.send + ' ↗'; updateInput(); }
    });
  } else {
    const widget = $('widget');
    window.onTelegramAuth = async user => {
      status(labels.signingIn);
      try {
        await request(panel.dataset.loginUrl, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({telegram_payload: user})});
        location.hash = 'comments-section'; location.reload();
      } catch (error) { status(error.message, true); }
    };
    if (widget.dataset.bot) {
      widget.replaceChildren(); const script = document.createElement('script');
      script.src = 'https://telegram.org/js/telegram-widget.js?22'; script.async = true;
      script.dataset.telegramLogin = widget.dataset.bot; script.dataset.size = 'large'; script.dataset.radius = '20';
      script.dataset.lang = lang === 'ru' ? 'ru' : lang === 'en' ? 'en' : 'uz'; script.dataset.onauth = 'onTelegramAuth(user)'; script.dataset.requestAccess = 'write';
      script.onerror = () => { widget.textContent = labels.noLogin; }; widget.append(script);
    } else widget.textContent = labels.noLogin;
  }
  document.addEventListener('click', event => { panel.querySelectorAll('.discussion-picker[open]').forEach(picker => { if (!picker.contains(event.target)) picker.open = false; }); });
  panel.addEventListener('keydown', event => { if (event.key === 'Escape') panel.querySelectorAll('.discussion-picker[open]').forEach(picker => { picker.open = false; picker.querySelector('summary').focus(); }); });
  async function focusComment() {
    const match = location.hash.match(/^#comment-(\d+)$/); if (!match) return;
    let node = document.getElementById(`comment-${match[1]}`); if (node) return goTo(node);
    try {
      const data = await request(listURL({focus: match[1]}));
      if (!data.focus_thread) return;
      addComment(data.focus_thread, $('list'), true);
      if (data.focus_thread.id !== Number(match[1])) {
        const thread = threads.get(data.focus_thread.id); thread.replies.hidden = false; thread.toggle.setAttribute('aria-expanded', 'true'); thread.toggle.textContent = labels.hideReplies;
        await loadReplies(data.focus_thread.id, match[1]);
      } else goTo(document.getElementById(`comment-${match[1]}`));
    } catch (error) { status(error.message, true); }
  }
  window.addEventListener('hashchange', focusComment); focusComment();
})();
