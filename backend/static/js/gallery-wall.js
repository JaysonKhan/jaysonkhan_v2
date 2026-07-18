/* gallery-wall.js — footer tepasidagi "Gallery Wall" avto-paginatsiyasi.
   Sahifalar JSON feed'dan (til-prefiksli {% url %} — CLAUDE.md gotcha #12)
   sakratmasdan tortiladi: yangi kadrlar img.decode() dan KEYIN, birin-ketin
   fade-up bo'lib qo'shiladi; tugma joyi min-height bilan band — UI sakramaydi.
   Devor oxiriga yaqinlashganda IntersectionObserver keyingi sahifani O'ZI
   yuklaydi (600px oldindan); tugma fallback/retry uchun qoladi — xatoda
   avto-yuklash pauza bo'lib, qo'lda retry kutiladi.
   Oxirgi sahifadan keyin tugma yumshoq yo'qoladi, hisoblagich qoladi. */
(function () {
  var wall = document.getElementById("gallery-wall");
  var moreBtn = document.getElementById("gw-more");
  if (!wall || !moreBtn) return;

  var FEED_URL = wall.dataset.feedUrl;
  var shownEl = document.getElementById("gw-shown");
  var nextPage = 2;
  var loading = false;
  // Birinchi qator darhol (eager), qolgani lazy — 20 kadrni birdan tortmaslik uchun
  var EAGER_COUNT = 6;

  function makeItem(img, idx) {
    var fig = document.createElement("figure");
    fig.className = "gw-item lightbox-trigger";
    fig.style.setProperty("--ar", img.ar || "1.5");
    fig.tabIndex = 0;
    fig.setAttribute("role", "button");
    fig.setAttribute("aria-label", img.hint || "");
    // lightbox.js delegatsiya orqali ochadi: cover ko'rinadi, full ochiladi
    fig.setAttribute("data-lightbox", "");
    fig.setAttribute("data-full", img.full || img.url);
    if (img.full_ar) fig.setAttribute("data-full-ar", img.full_ar);
    fig.setAttribute("data-hint", img.hint || "");

    var im = document.createElement("img");
    im.src = img.url;
    im.alt = img.hint || "";
    // lazy kadrlar decode() da settle bo'lmaydi — reveal poygasi (load/timeout) qoplaydi
    im.loading = idx < EAGER_COUNT ? "eager" : "lazy";
    im.decoding = "async";
    if (img.w) im.width = img.w;
    if (img.h) im.height = img.h;

    var cap = document.createElement("figcaption");
    cap.className = "gw-hint";
    cap.textContent = img.hint || "";

    fig.append(im, cap);
    return fig;
  }

  function setBtn(label, disabled) {
    moreBtn.disabled = disabled;
    moreBtn.firstChild.nodeValue = label + " ";
  }

  function finish() {
    moreBtn.classList.add("is-done");
    if (io) io.disconnect();
    // O'rin band qolaveradi (.gw-more-wrap min-height) — layout sakramaydi
    setTimeout(function () {
      moreBtn.hidden = true;
    }, 450);
  }

  function loadMore() {
    if (loading || moreBtn.hidden) return;
    loading = true;
    setBtn(moreBtn.dataset.labelLoading, true);

    // Timeout'siz osilgan so'rov tugmani abadiy "loading"da qoldirardi
    var ctrl =
      typeof AbortController === "function" ? new AbortController() : null;
    var killTimer = ctrl
      ? setTimeout(function () {
          ctrl.abort();
        }, 12000)
      : 0;

    fetch(FEED_URL + "?page=" + nextPage, {
      headers: { "Accept-Language": document.documentElement.lang || "xo" },
      signal: ctrl ? ctrl.signal : undefined,
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var items = (data.images || []).map(makeItem);
        // Bitta fragment = bitta reflow (20 ta alohida appendChild o'rniga)
        var frag = document.createDocumentFragment();
        items.forEach(function (fig) {
          frag.appendChild(fig);
        });
        wall.appendChild(frag);

        // Rasm tayyor bo'lgach birin-ketin fade-up; decode/load/timeout —
        // qaysi biri birinchi kelsa (decode ba'zan settle bo'lmaydi)
        items.forEach(function (fig, i) {
          var im = fig.querySelector("img");
          var done = false;
          var reveal = function () {
            if (done) return;
            done = true;
            setTimeout(function () {
              fig.classList.add("is-in");
            }, i * 45);
          };
          if (im.decode) {
            im.decode().then(reveal, reveal);
          }
          im.addEventListener("load", reveal);
          im.addEventListener("error", reveal);
          setTimeout(reveal, 700);
        });

        if (shownEl) {
          shownEl.textContent = String(
            parseInt(shownEl.textContent, 10) + items.length,
          );
        }

        nextPage++;
        setBtn(moreBtn.dataset.labelMore, false);
        if (!data.has_next) {
          finish();
        } else {
          poke(); // wrap hali ko'rinib turgan bo'lsa keyingi sahifani darhol boshlaydi
        }
      })
      .catch(function (err) {
        console.error("Gallery feed failed", err);
        autoPaused = true; // xatoda avto-yuklashni to'xtatamiz — retry qo'lda
        setBtn(moreBtn.dataset.labelRetry, false);
      })
      .finally(function () {
        if (killTimer) clearTimeout(killTimer);
        loading = false;
      });
  }

  moreBtn.addEventListener("click", function () {
    autoPaused = false;
    loadMore();
  });

  // Avto-paginatsiya: devor oxiri (tugma atrofi) ko'rinishga 600px qolganda
  // keyingi sahifa o'zi yuklanadi. IO threshold-kesishmada otiladi — sahifa
  // qo'shilgach wrap hali ham ko'rinib tursa, poke() qayta kuzatib yana otdiradi.
  var autoPaused = false;
  var io = null;
  var wrap = moreBtn.parentElement;

  function poke() {
    if (!io || moreBtn.hidden) return;
    io.unobserve(wrap);
    io.observe(wrap);
  }

  if ("IntersectionObserver" in window && wrap) {
    io = new IntersectionObserver(
      function (entries) {
        if (!entries[0].isIntersecting) return;
        if (loading || autoPaused || moreBtn.hidden) return;
        loadMore();
      },
      { rootMargin: "600px 0px" },
    );
    io.observe(wrap);
  }
})();
