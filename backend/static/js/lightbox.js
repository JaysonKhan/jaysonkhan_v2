/* lightbox.js — hero-animatsiyali rasm ochish (gallery wall + about).
   Trigger: `[data-lightbox]` element ichidagi ko'rinadigan <img> (anime cover).
   Bosilganda: cover thumbnail'dan FLIP (transform) bilan markazga "uchadi",
   yetib borgach asosiy (real) rasmga yumshoq crossfade bo'ladi.
   Yopish: backdrop, ×, yoki Esc — teskari FLIP bilan thumbnailga qaytadi.
   reduced-motion: FLIP yo'q, oddiy fade; asosiy rasm darhol ko'rinadi.
   Bitta global overlay; delegatsiya bilan ishlaydi (dinamik gallery kadrlariga ham). */
(function () {
  var OPEN_MS = 420;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var overlay = null;
  var lastTrigger = null;
  var animating = false;

  function buildOverlay() {
    var o = document.createElement("div");
    o.className = "lb-overlay";
    o.setAttribute("role", "dialog");
    o.setAttribute("aria-modal", "true");

    var backdrop = document.createElement("div");
    backdrop.className = "lb-backdrop";

    var stage = document.createElement("div");
    stage.className = "lb-stage";
    var coverImg = document.createElement("img");
    coverImg.className = "lb-img lb-cover";
    coverImg.alt = "";
    var fullImg = document.createElement("img");
    fullImg.className = "lb-img lb-full";
    fullImg.alt = "";
    stage.append(coverImg, fullImg);

    var cap = document.createElement("figcaption");
    cap.className = "lb-cap";

    var spinner = document.createElement("div");
    spinner.className = "lb-spin";
    spinner.innerHTML =
      '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56" stroke-linecap="round"/></svg>';

    var close = document.createElement("button");
    close.type = "button";
    close.className = "lb-close";
    close.setAttribute("aria-label", "Close");
    close.innerHTML =
      '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';

    o.append(backdrop, stage, spinner, cap, close);
    document.body.appendChild(o);

    backdrop.addEventListener("click", closeLightbox);
    close.addEventListener("click", closeLightbox);
    stage.addEventListener("click", closeLightbox);

    return {
      root: o,
      stage: stage,
      cover: coverImg,
      full: fullImg,
      cap: cap,
      spinner: spinner,
    };
  }

  function targetRect(ar) {
    var vw = window.innerWidth,
      vh = window.innerHeight;
    var maxW = Math.min(vw * 0.92, 1400);
    var maxH = vh * 0.9;
    var tw = maxW,
      th = tw / ar;
    if (th > maxH) {
      th = maxH;
      tw = th * ar;
    }
    return { w: tw, h: th, x: (vw - tw) / 2, y: (vh - th) / 2 };
  }

  function openLightbox(trigger) {
    if (animating) return;
    var img = trigger.querySelector("img");
    if (!img) return;
    lastTrigger = trigger;

    var coverSrc = img.currentSrc || img.src;
    var fullSrc = trigger.dataset.full || coverSrc;
    var hint = trigger.dataset.hint || img.alt || "";
    var ar =
      parseFloat(trigger.dataset.fullAr || "0") ||
      (img.naturalWidth && img.naturalHeight
        ? img.naturalWidth / img.naturalHeight
        : 1);

    if (!overlay) overlay = buildOverlay();
    var lb = overlay;

    lb.cover.src = coverSrc;
    lb.full.src = "";
    lb.full.classList.remove("is-shown");
    lb.cap.textContent = hint;
    lb.cap.classList.toggle("has-text", !!hint);

    var t = targetRect(ar);
    lb.stage.style.left = t.x + "px";
    lb.stage.style.top = t.y + "px";
    lb.stage.style.width = t.w + "px";
    lb.stage.style.height = t.h + "px";

    document.documentElement.classList.add("lb-open");
    lb.root.classList.add("is-visible");

    var rect = img.getBoundingClientRect();

    if (reduce) {
      lb.root.classList.add("is-open");
      loadFull(lb, fullSrc);
      return;
    }

    // FLIP: stage'ni target'ga qo'ydik; teskari transform bilan thumbnailga "qaytaramiz"
    var sx = rect.width / t.w,
      sy = rect.height / t.h;
    var dx = rect.left - t.x,
      dy = rect.top - t.y;
    lb.stage.style.transition = "none";
    lb.stage.style.transformOrigin = "top left";
    lb.stage.style.transform =
      "translate(" + dx + "px," + dy + "px) scale(" + sx + "," + sy + ")";

    animating = true;
    // reflow, keyin identity'ga animatsiya
    void lb.stage.offsetWidth;
    requestAnimationFrame(function () {
      lb.root.classList.add("is-open");
      lb.stage.style.transition =
        "transform " + OPEN_MS + "ms cubic-bezier(0.16,1,0.3,1)";
      lb.stage.style.transform = "none";
    });

    var onEnd = function (e) {
      if (e.propertyName !== "transform") return;
      lb.stage.removeEventListener("transitionend", onEnd);
      animating = false;
      loadFull(lb, fullSrc);
    };
    lb.stage.addEventListener("transitionend", onEnd);
    // fallback
    setTimeout(function () {
      if (animating) {
        animating = false;
        loadFull(lb, fullSrc);
      }
    }, OPEN_MS + 120);
  }

  function loadFull(lb, fullSrc) {
    if (!fullSrc || fullSrc === lb.cover.src) return; // cover = full bo'lsa reveal shart emas
    lb.spinner.classList.add("is-on");
    var pre = new Image();
    pre.onload = function () {
      lb.full.src = fullSrc;
      requestAnimationFrame(function () {
        lb.full.classList.add("is-shown");
        lb.spinner.classList.remove("is-on");
      });
    };
    pre.onerror = function () {
      lb.spinner.classList.remove("is-on");
    };
    pre.src = fullSrc;
  }

  function closeLightbox() {
    if (!overlay || !overlay.root.classList.contains("is-visible") || animating)
      return;
    var lb = overlay;
    document.documentElement.classList.remove("lb-open");

    if (reduce || !lastTrigger) {
      lb.root.classList.remove("is-open", "is-visible");
      return;
    }
    var img = lastTrigger.querySelector("img");
    var rect = img.getBoundingClientRect();
    // Yopishda cover'ni qaytaramiz (thumbnail cover ko'rsatadi → seamless)
    lb.full.classList.remove("is-shown");

    var tw = parseFloat(lb.stage.style.width),
      th = parseFloat(lb.stage.style.height);
    var tx = parseFloat(lb.stage.style.left),
      ty = parseFloat(lb.stage.style.top);
    var sx = rect.width / tw,
      sy = rect.height / th;
    var dx = rect.left - tx,
      dy = rect.top - ty;

    animating = true;
    lb.root.classList.remove("is-open");
    lb.stage.style.transition =
      "transform " + OPEN_MS + "ms cubic-bezier(0.16,1,0.3,1)";
    lb.stage.style.transform =
      "translate(" + dx + "px," + dy + "px) scale(" + sx + "," + sy + ")";

    var onEnd = function (e) {
      if (e.propertyName !== "transform") return;
      lb.stage.removeEventListener("transitionend", onEnd);
      lb.root.classList.remove("is-visible");
      lb.stage.style.transition = "none";
      lb.stage.style.transform = "none";
      animating = false;
    };
    lb.stage.addEventListener("transitionend", onEnd);
    setTimeout(function () {
      if (animating) {
        lb.root.classList.remove("is-visible");
        lb.stage.style.transition = "none";
        lb.stage.style.transform = "none";
        animating = false;
      }
    }, OPEN_MS + 120);
  }

  // Delegatsiya — server-render va dinamik (gallery-wall.js) kadrlar uchun
  document.addEventListener("click", function (e) {
    var trigger = e.target.closest("[data-lightbox]");
    if (trigger) {
      e.preventDefault();
      openLightbox(trigger);
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeLightbox();
      return;
    }
    if (e.key === "Enter" || e.key === " ") {
      var trigger = e.target.closest && e.target.closest("[data-lightbox]");
      if (trigger && document.activeElement === trigger) {
        e.preventDefault();
        openLightbox(trigger);
      }
    }
  });
})();
