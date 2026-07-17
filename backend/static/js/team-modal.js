/* team-modal.js — jamoa a'zosi detail modali (hero FLIP: karta → panel).
   Karta bosilganda panel karta o'rnidan markazga "o'sib" chiqadi; ichidagi
   anime portret bosilganda real portretga crossfade bo'ladi (photo_real
   bo'lsa; "Tap to reveal" cue). Yopish: backdrop / × / Esc — teskari FLIP.
   Ma'lumot: {{ team_payload|json_script }} → faqat textContent bilan DOMga
   (XSS yo'q); linklar http(s) validatsiyadan o'tadi.
   rAF-throttle muhitida fallback'lar ochilishni kafolatlaydi (lightbox.js
   bilan bir xil qoida — memory: rAF'gagina bog'lanma). */
(function () {
  var dataEl = document.getElementById("team-data");
  var cfgEl = document.getElementById("team-modal-cfg");
  if (!dataEl) return;
  var DATA;
  try {
    DATA = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }
  var L = (cfgEl && cfgEl.dataset) || {};

  var OPEN_MS = 420;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var overlay = null;
  var lastCard = null;
  var animating = false;
  var openSeq = 0; // eskirgan real-portret preload'ini o'ldirish uchun

  function el(tag, cls) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    return n;
  }

  function buildOverlay() {
    var o = el("div", "tm-overlay");
    o.setAttribute("role", "dialog");
    o.setAttribute("aria-modal", "true");

    var backdrop = el("div", "tm-backdrop");
    var panel = el("div", "tm-panel");

    var head = el("div", "tm-head");
    var photo = el("div", "tm-photo");
    photo.setAttribute("role", "button");
    photo.tabIndex = 0;
    var imgA = el("img", "tm-img tm-img--anime");
    imgA.alt = "";
    imgA.decoding = "async";
    var imgR = el("img", "tm-img tm-img--real");
    imgR.alt = "";
    imgR.decoding = "async";
    var initials = el("span", "tm-initials");
    var cue = el("span", "tm-cue");
    cue.textContent = L.labelReveal || "Tap to reveal";
    cue.setAttribute("aria-hidden", "true");
    photo.append(imgA, imgR, initials, cue);

    var who = el("div", "tm-who");
    var name = el("h3", "tm-name");
    var role = el("span", "mono-label tm-role");
    var meta = el("span", "tm-meta");
    who.append(name, role, meta);
    head.append(photo, who);

    var quote = el("p", "tm-quote");
    var bio = el("p", "tm-bio");
    var skills = el("div", "tm-skills");
    var links = el("div", "tm-links");

    var close = el("button", "tm-close");
    close.type = "button";
    close.setAttribute("aria-label", L.labelClose || "Close");
    close.innerHTML =
      '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';

    panel.append(close, head, quote, bio, skills, links);
    o.append(backdrop, panel);
    document.body.appendChild(o);

    backdrop.addEventListener("click", closeModal);
    close.addEventListener("click", closeModal);

    // Portret bosilganda anime ↔ real almashadi (real bo'lsagina)
    function toggleReal(e) {
      if (!photo.classList.contains("has-real")) return;
      if (e) e.stopPropagation();
      photo.classList.toggle("is-real");
    }
    photo.addEventListener("click", toggleReal);
    photo.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleReal(e);
      }
    });

    return {
      root: o,
      panel: panel,
      photo: photo,
      imgA: imgA,
      imgR: imgR,
      initials: initials,
      name: name,
      role: role,
      meta: meta,
      quote: quote,
      bio: bio,
      skills: skills,
      links: links,
      close: close,
    };
  }

  function safeUrl(u) {
    return /^https?:\/\//i.test(u || "") ? u : "";
  }

  function fill(lb, m, seq) {
    lb.name.textContent = m.name || "";
    lb.role.textContent = m.role || "";
    lb.meta.textContent = m.years ? m.years + " " + (L.labelYears || "y") : "";
    lb.quote.textContent = m.quote ? "“" + m.quote + "”" : "";
    lb.quote.hidden = !m.quote;
    lb.bio.textContent = m.bio || "";

    lb.skills.textContent = "";
    (m.skills || []).forEach(function (s) {
      var t = el("span", "tag");
      t.textContent = s;
      lb.skills.appendChild(t);
    });

    lb.links.textContent = "";
    [
      ["Telegram", safeUrl(m.telegram)],
      ["GitHub", safeUrl(m.github)],
      ["LinkedIn", safeUrl(m.linkedin)],
    ].forEach(function (pair) {
      if (!pair[1]) return;
      var a = el("a", "btn btn-sm tm-link");
      a.href = pair[1];
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = pair[0];
      lb.links.appendChild(a);
    });
    lb.links.hidden = !lb.links.childNodes.length;

    // Portret: anime bilan ochiladi (karta bilan seamless), real yuklangach
    // avtomatik REAL'ga crossfade bo'ladi; bosilganda anime'ga qaytadi
    lb.photo.classList.remove("is-real", "has-real");
    lb.imgR.removeAttribute("src");
    if (m.photo) {
      lb.imgA.src = m.photo;
      lb.imgA.hidden = false;
      lb.initials.hidden = true;
      var real = m.photo_real || "";
      if (real) {
        var pre = new Image();
        pre.onload = function () {
          if (seq !== openSeq) return; // boshqa a'zo ochilgan — eskirgan yuklash
          lb.imgR.src = real;
          lb.photo.classList.add("has-real", "is-real");
        };
        pre.src = real;
      }
    } else {
      lb.imgA.hidden = true;
      lb.imgA.removeAttribute("src");
      lb.initials.hidden = false;
      lb.initials.textContent = m.initials || "";
    }
  }

  function openModal(card) {
    if (animating) return;
    var m = DATA[card.dataset.teamId];
    if (!m) return;
    lastCard = card;

    if (!overlay) overlay = buildOverlay();
    var lb = overlay;
    var seq = ++openSeq;
    fill(lb, m, seq);

    document.documentElement.classList.add("tm-open");
    lb.root.classList.add("is-visible");
    lb.close.focus({ preventScroll: true });

    if (reduce) {
      lb.root.classList.add("is-open");
      return;
    }

    // FLIP: panel yakuniy (markaz) holatda o'lchanadi, karta o'rnidan boshlanadi
    var pr = lb.panel.getBoundingClientRect();
    var cr = card.getBoundingClientRect();
    var sx = cr.width / pr.width,
      sy = cr.height / pr.height;
    var dx = cr.left - pr.left,
      dy = cr.top - pr.top;
    lb.panel.style.transition = "none";
    lb.panel.style.transformOrigin = "top left";
    lb.panel.style.transform =
      "translate(" + dx + "px," + dy + "px) scale(" + sx + "," + sy + ")";

    animating = true;
    void lb.panel.offsetWidth;
    requestAnimationFrame(function () {
      lb.root.classList.add("is-open");
      lb.panel.style.transition =
        "transform " + OPEN_MS + "ms cubic-bezier(0.16,1,0.3,1)";
      lb.panel.style.transform = "none";
    });

    var onEnd = function (e) {
      if (e.propertyName !== "transform") return;
      lb.panel.removeEventListener("transitionend", onEnd);
      if (seq !== openSeq) return; // eskirgan listener (throttle'da kech otiladi)
      animating = false;
    };
    lb.panel.addEventListener("transitionend", onEnd);
    // Fallback: rAF/transition throttle bo'lsa ham modal ochilib bo'lsin.
    // Listener'ni BU YERDA ham olib tashlaymiz — aks holda yig'ilib qolib,
    // renderer uyg'onganda kech otilib keyingi ochilishni buzadi.
    setTimeout(function () {
      lb.panel.removeEventListener("transitionend", onEnd);
      if (seq !== openSeq) return;
      lb.root.classList.add("is-open");
      if (animating) {
        animating = false;
        lb.panel.style.transition = "none";
        lb.panel.style.transform = "none";
      }
    }, OPEN_MS + 120);
  }

  function closeModal() {
    if (!overlay || !overlay.root.classList.contains("is-visible") || animating)
      return;
    var lb = overlay;
    var seq = ++openSeq;
    document.documentElement.classList.remove("tm-open");
    if (lastCard && lastCard.focus) {
      lastCard.focus({ preventScroll: true });
    }

    if (reduce || !lastCard) {
      lb.root.classList.remove("is-open", "is-visible");
      return;
    }

    var pr = lb.panel.getBoundingClientRect();
    var cr = lastCard.getBoundingClientRect();
    var sx = cr.width / pr.width,
      sy = cr.height / pr.height;
    var dx = cr.left - pr.left,
      dy = cr.top - pr.top;

    animating = true;
    lb.root.classList.remove("is-open");
    lb.panel.style.transition =
      "transform " + OPEN_MS + "ms cubic-bezier(0.16,1,0.3,1)";
    lb.panel.style.transform =
      "translate(" + dx + "px," + dy + "px) scale(" + sx + "," + sy + ")";

    var done = function () {
      lb.root.classList.remove("is-visible");
      lb.panel.style.transition = "none";
      lb.panel.style.transform = "none";
      animating = false;
    };
    var onEnd = function (e) {
      if (e.propertyName !== "transform") return;
      lb.panel.removeEventListener("transitionend", onEnd);
      if (seq !== openSeq) return; // eskirgan — yangi ochilgan modalni yopmasin
      done();
    };
    lb.panel.addEventListener("transitionend", onEnd);
    setTimeout(function () {
      lb.panel.removeEventListener("transitionend", onEnd);
      if (seq !== openSeq) return;
      if (animating) done();
    }, OPEN_MS + 120);
  }

  // Delegatsiya: karta click / Enter / Space
  document.addEventListener("click", function (e) {
    var card = e.target.closest("[data-team-id]");
    if (card && !e.target.closest("a")) {
      openModal(card);
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeModal();
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      var card = e.target.closest && e.target.closest("[data-team-id]");
      if (card && document.activeElement === card) {
        e.preventDefault();
        openModal(card);
      }
    }
  });
})();
