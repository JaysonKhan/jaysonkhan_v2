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
  const editors = new Map();
  const editorTemplate = loggedIn ? $('form').cloneNode(true) : null;
  let activeReply = null, mutations = 0;
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
    try { response = await fetch(url, {...options, credentials: 'same-origin', headers: {'Accept-Language': lang, 'X-CSRFToken': panel.querySelector('[name=csrfmiddlewaretoken]')?.value || '', ...options.headers}}); }
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
    if (comment.is_deleted) return;
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
    if (!comment.is_deleted) {
      const reply = button(labels.reply, 'discussion-text-btn', event => openReply(comment, event.currentTarget));
      reply.dataset.reply = comment.id; reply.setAttribute('aria-expanded', 'false');
      reply.setAttribute('aria-controls', `reply-form-${comment.id}`); bar.append(reply);
    }
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
    if (comment.is_deleted) row.classList.add('is-deleted');
    const body = el('div', 'discussion-comment-body');
    const header = el('header'); header.append(el('strong', '', comment.author.display_name));
    if (comment.is_own) header.append(el('span', 'discussion-you', labels.you));
    const permalink = el('a', 'discussion-time'); permalink.href = `#comment-${comment.id}`; permalink.title = labels.link;
    const time = el('time', '', formatDate(comment.created_at)); time.dateTime = comment.created_at; permalink.append(time); header.append(permalink); body.append(header);
    if (comment.is_own) {
      const menu = el('details', 'discussion-owner-menu');
      const summary = el('summary', 'discussion-text-btn', '···'); summary.setAttribute('aria-label', labels.actions);
      const options = el('div', 'discussion-owner-options');
      options.append(button(labels.deleteComment, 'discussion-text-btn', () => { menu.open = false; confirmDelete(comment, body, summary); }));
      menu.append(summary, options); header.append(menu);
    }
    if (comment.reply_to && comment.reply_to.id !== comment.parent_id) {
      const target = el('a', 'discussion-reply-to', labels.replyingTo.replace('{name}', comment.reply_to.name));
      target.href = `#comment-${comment.reply_to.id}`; body.append(target);
    }
    if (comment.text) {
      const text = el('p', 'discussion-text', comment.text); body.append(text);
      if (comment.text.length > 360 || comment.text.split('\n').length > 5) {
        text.classList.add('is-collapsed');
        const more = button(labels.readMore, 'discussion-text-btn discussion-read-more', () => {
          const collapsed = text.classList.toggle('is-collapsed'); more.textContent = collapsed ? labels.readMore : labels.showLess;
          more.setAttribute('aria-expanded', String(!collapsed));
        });
        more.setAttribute('aria-expanded', 'false'); body.append(more);
      }
    }
    if (comment.image_url && safeURL(comment.image_url)) {
      const link = el('a', 'discussion-image lightbox-trigger'); link.href = safeURL(comment.image_url);
      link.dataset.lightbox = ''; link.dataset.full = link.href; link.dataset.hint = `${labels.image} · ${comment.author.display_name}`; link.dataset.closeLabel = labels.close;
      const image = el('img'); image.src = link.href; image.alt = labels.image; image.loading = 'lazy';
      link.append(image, el('span', 'discussion-image-caption', labels.image + ' ↗')); body.append(link);
    }
    const actions = el('div', 'discussion-actions'); renderReactions(comment, actions); body.append(actions, el('div', 'discussion-inline-slot'));
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
    attachEditor(comment.id);
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
    updateEmpty();
    $('count').textContent = data.discussion_count;
    page = data.page; hasNext = data.has_next; $('more').hidden = !hasNext;
  }
  async function loadComments(reset = false) {
    if (mutations || (loading && !reset)) return;
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
    if (mutations) return;
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
  function updateEmpty() {
    const empty = $('list').querySelector(':scope > .discussion-empty');
    if ($('list').querySelector(':scope > article')) empty?.remove();
    else if (!empty) $('list').append(el('p', 'discussion-empty', labels.empty));
  }
  function lockList(start) {
    mutations += start ? 1 : -1;
    if (start) { controller?.abort(); ++generation; loading = false; $('list').removeAttribute('aria-busy'); $('more').textContent = labels.moreComments; }
    panel.querySelectorAll('[data-sort], #discussion-more').forEach(node => { node.disabled = mutations > 0; });
  }
  function attachEditor(id) {
    const editor = editors.get(id); const row = document.getElementById(`comment-${id}`);
    if (!editor || !row) return;
    row.querySelector(':scope > .discussion-comment-body > .discussion-inline-slot').append(editor.form);
    row.querySelector('[data-reply]')?.setAttribute('aria-expanded', String(!editor.form.hidden));
  }
  function openReply(comment, trigger) {
    if (!loggedIn) return requireLogin();
    if (activeReply && activeReply !== comment.id) editors.get(activeReply)?.close(false);
    let editor = editors.get(comment.id);
    if (!editor) {
      const form = editorTemplate.cloneNode(true); form.id = `reply-form-${comment.id}`;
      form.classList.add('discussion-inline-form');
      editor = makeEditor(form, comment); editors.set(comment.id, editor);
    }
    activeReply = comment.id; editor.trigger = trigger; editor.form.hidden = false; attachEditor(comment.id);
    trigger.setAttribute('aria-expanded', 'true');
    editor.text.focus({preventScroll: true});
    // Scroll only if the inline editor is below the visible viewport.
    const bounds = editor.text.getBoundingClientRect();
    if (bounds.bottom > innerHeight - 30 || bounds.top < 90) {
      window.scrollTo({top: scrollY + bounds.top - Math.min(innerHeight * .45, 220), behavior: reduced ? 'auto' : 'smooth'});
    }
  }
  function makeEditor(form, target = null) {
    const suffix = target ? `-${target.id}` : '';
    form.querySelectorAll('[id]').forEach(node => { node.dataset.field = node.id.replace('discussion-', ''); node.id += suffix; });
    if (target) form.querySelectorAll('[for], [aria-describedby]').forEach(node => {
      ['for', 'aria-describedby'].forEach(attr => { if (node.hasAttribute(attr)) node.setAttribute(attr, node.getAttribute(attr).split(' ').map(id => id + suffix).join(' ')); });
    });
    const f = key => form.querySelector(`[data-field="${key}"]`);
    let selectedFile = null, previewURL = null, sending = false;
    const key = target ? `${draftKey}:reply:${target.id}` : draftKey;
    const error = message => { f('form-error').textContent = message; f('form-error').hidden = !message; };
    const save = () => { try { sessionStorage.setItem(key, JSON.stringify({text:f('text').value, time:Date.now()})); } catch (_) {} };
    function update() {
      const text = f('text').value; const count = Array.from(text).length;
      f('chars').textContent = `${count} / ${limits.maxLength}`;
      f('send').disabled = sending || count > limits.maxLength || (text.trim().length < limits.minLength && !selectedFile);
    }
    function clearImage() {
      if (previewURL) URL.revokeObjectURL(previewURL); previewURL = null; selectedFile = null;
      f('image').value = ''; f('preview-image').removeAttribute('src'); f('preview').hidden = true; update();
    }
    const editor = {form, text:f('text'), trigger:null, close(focus = true) {
      if (sending) return;
      form.hidden = true; save(); if (activeReply === target?.id) activeReply = null;
      const trigger = document.querySelector(`[data-reply="${target?.id}"]`);
      trigger?.setAttribute('aria-expanded', 'false'); if (focus) trigger?.focus({preventScroll:true});
    }};
    if (target) {
      f('text').rows = 2; f('text').placeholder = labels.writeReply;
      form.querySelector(`label[for="${f('text').id}"]`).textContent = labels.replyingTo.replace('{name}',target.author.display_name);
      f('send').textContent = labels.postReply + ' ↗'; f('cancel').hidden = false;
      f('cancel').addEventListener('click', () => editor.close());
    }
    try { const draft = JSON.parse(sessionStorage.getItem(key)); if (draft && Date.now()-draft.time < 86400000 && draft.text) f('text').value = draft.text; } catch (_) {}
    update();
    f('text').addEventListener('input', () => { update(); error(''); save(); });
    f('text').addEventListener('keydown', event => {
      if (event.key === 'Escape' && target) { event.preventDefault(); editor.close(); }
      if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.isComposing) { event.preventDefault(); if (!f('send').disabled) form.requestSubmit(); }
    });
    f('remove-image').addEventListener('click', () => { clearImage(); f('image').focus(); });
    f('image').addEventListener('change', () => {
      const file = f('image').files[0]; if (!file) return;
      if (!['image/jpeg','image/png','image/gif','image/webp'].includes(file.type) || file.size > limits.maxImageMB * 1024 * 1024) {
        clearImage(); error(labels.imageHint.replace('{n}',limits.maxImageMB)); return;
      }
      if (previewURL) URL.revokeObjectURL(previewURL);
      selectedFile = file; previewURL = URL.createObjectURL(file); f('preview-image').src = previewURL;
      f('file-name').textContent = file.name; f('preview').hidden = false; error(''); update();
    });
    form.addEventListener('submit', async event => {
      event.preventDefault(); if (sending) return;
      const text = f('text').value.trim();
      if (Array.from(text).length > limits.maxLength) return error(labels.maxChars.replace('{n}',limits.maxLength));
      if (text.length < limits.minLength && !selectedFile) return error(labels.minChars.replace('{n}',limits.minLength));
      const body = new FormData(); body.append('text', text); if (target) body.append('parent_id',target.id); if (selectedFile) body.append('image',selectedFile);
      sending = true; lockList(true); form.querySelector('fieldset').disabled = true; f('send').textContent = labels.sending; error('');
      try {
        const data = await request(form.action,{method:'POST',body});
        f('text').value = ''; save(); clearImage();
        if (data.comment) {
          const c = data.comment;
          if (c.parent_id) {
            let thread = threads.get(c.parent_id);
            if (!thread) {
              const found = await request(listURL({focus:c.id}));
              if (found.focus_thread) addComment(found.focus_thread,$('list'),true);
              thread = threads.get(c.parent_id);
            }
            if (thread) {
              thread.replies.hidden = false; thread.toggle.hidden = false;
              thread.toggle.textContent = labels.hideReplies; thread.toggle.setAttribute('aria-expanded','true');
              // Focus pagination gives a contiguous page containing the new reply.
              thread.list.replaceChildren(); thread.loaded = false; thread.page = 0;
              await loadReplies(c.parent_id,c.id);
              addComment(c,thread.list);
            }
          } else addComment(c,$('list'),true);
          $('count').textContent = Number($('count').textContent)+1; updateEmpty();
          const node = document.getElementById(`comment-${c.id}`); if (node) goTo(node);
          if (target) { sending = false; editor.close(false); }
          else status(data.message);
        } else {
          const note = el('p','discussion-help', target ? labels.pendingReply : data.message); note.setAttribute('role','status'); form.after(note);
          if (target) { sending = false; editor.close(false); }
        }
      } catch (failure) { error(failure.message); }
      finally { sending = false; lockList(false); form.querySelector('fieldset').disabled = false; f('send').textContent = (target ? labels.postReply : labels.send)+' ↗'; update(); }
    });
    return editor;
  }
  function replaceRoot(comment) {
    const old = document.getElementById(`comment-${comment.id}`); const thread = threads.get(comment.id);
    const row = createComment(comment);
    if (old) old.replaceWith(row); else $('list').prepend(row);
    if (thread?.loaded) {
      const fresh = threads.get(comment.id);
      fresh.replies.replaceWith(thread.replies); fresh.replies = thread.replies;
      Object.assign(fresh,{list:thread.list,earlier:thread.earlier,more:thread.more,page:thread.page,firstPage:thread.firstPage,loaded:true,count:comment.reply_count});
      fresh.toggle.setAttribute('aria-expanded',String(!fresh.replies.hidden));
      fresh.toggle.textContent = fresh.replies.hidden ? `${labels.replies} · ${fresh.count}` : labels.hideReplies;
    }
    attachEditor(comment.id); updateEmpty();
  }
  async function refreshReplies(id) {
    const thread = threads.get(id); if (!thread?.loaded) return;
    const pages = Math.max(1,thread.page); const replies = [];
    let last;
    for (let current=1;current<=pages;current++) {
      const url = new URL(urlFor(panel.dataset.repliesUrl,id),location.href); url.searchParams.set('page',current);
      last = await request(url); replies.push(...last.replies); if (!last.has_next) break;
    }
    if (!thread.replies.isConnected) return;
    thread.list.replaceChildren(); replies.forEach(reply => addComment(reply,thread.list));
    thread.firstPage = 1; thread.page = last.page; thread.count = last.total_count;
    thread.earlier.hidden = true; thread.more.hidden = !last.has_next;
  }
  function confirmDelete(comment, body, trigger) {
    if (body.querySelector(':scope > .discussion-delete-confirm')) return;
    const box = el('div','discussion-delete-confirm'); box.setAttribute('role','group'); box.setAttribute('aria-label',labels.deleteTitle);
    box.append(el('strong','',labels.deleteTitle),el('p','discussion-help',labels.deleteHint));
    const actions = el('div','discussion-confirm-actions');
    const cancel = button(labels.cancel,'btn',() => { box.remove(); trigger.focus({preventScroll:true}); });
    const remove = button(labels.delete,'btn discussion-danger',async () => {
      cancel.disabled = true; remove.disabled = true; lockList(true);
      try {
        const data = await request(urlFor(panel.dataset.deleteUrl,comment.id),{method:'POST'});
        const row = document.getElementById(`comment-${comment.id}`); const root = document.getElementById(`comment-${comment.parent_id || comment.id}`);
        const notice = el('div','discussion-notice'); notice.setAttribute('role','status'); notice.append(el('span','',labels.deleted));
        const undo = button(labels.undo,'discussion-text-btn',async () => {
          undo.disabled = true; lockList(true);
          try {
            const restored = await request(urlFor(panel.dataset.restoreUrl,comment.id),{method:'POST'});
            if (restored.thread) replaceRoot(restored.thread);
            if (restored.comment?.parent_id) {
              const thread = threads.get(restored.comment.parent_id);
              thread.replies.hidden = false; thread.toggle.setAttribute('aria-expanded','true'); thread.toggle.textContent = labels.hideReplies;
              if (thread.loaded) await refreshReplies(restored.comment.parent_id);
              else await loadReplies(restored.comment.parent_id,restored.comment.id);
            }
            $('count').textContent = restored.discussion_count; notice.textContent = labels.restored; updateEmpty();
          } catch (failure) { notice.append(el('span','discussion-error',failure.message)); undo.disabled = false; }
          finally { lockList(false); }
        });
        notice.append(undo);
        // Keep Undo visible even when the last reply removes its deleted root.
        if (comment.parent_id && data.thread) threads.get(comment.parent_id).list.before(notice);
        else root.before(notice);
        editors.get(comment.id)?.close(false); editors.delete(comment.id);
        if (!data.thread) { root.remove(); threads.delete(comment.parent_id || comment.id); }
        else if (!comment.parent_id) replaceRoot(data.thread);
        else { row.remove(); replaceRoot(data.thread); try { await refreshReplies(comment.parent_id); } catch (_) { status(labels.loadFailed,true); } }
        $('count').textContent = data.discussion_count; updateEmpty(); undo.focus({preventScroll:true});
        setTimeout(() => { undo.hidden = true; }, data.undo_seconds*1000);
      } catch (failure) { box.append(el('p','discussion-error',failure.message)); cancel.disabled = false; remove.disabled = false; }
      finally { lockList(false); }
    });
    actions.append(cancel,remove); box.append(actions); body.querySelector(':scope > .discussion-actions').after(box); cancel.focus({preventScroll:true});
  }
  if (loggedIn) {
    editors.set('root',makeEditor($('form')));
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
  document.addEventListener('click', event => { panel.querySelectorAll('.discussion-picker[open], .discussion-owner-menu[open]').forEach(picker => { if (!picker.contains(event.target)) picker.open = false; }); });
  panel.addEventListener('keydown', event => { if (event.key === 'Escape') panel.querySelectorAll('.discussion-picker[open], .discussion-owner-menu[open]').forEach(picker => { picker.open = false; picker.querySelector('summary').focus(); }); });
  async function focusComment() {
    const match = location.hash.match(/^#comment-(\d+)$/); if (!match) return;
    let node = document.getElementById(`comment-${match[1]}`);
    if (node) {
      const replies = node.closest('.discussion-replies');
      if (replies) { const thread = threads.get(Number(replies.id.replace('replies-',''))); replies.hidden = false; thread.toggle.setAttribute('aria-expanded','true'); thread.toggle.textContent = labels.hideReplies; }
      return goTo(node);
    }
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
