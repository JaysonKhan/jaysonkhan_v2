/* gallery-wall.js — footer tepasidagi "Gallery Wall" load-more mantiqi.
   Sahifalar JSON feed'dan (til-prefiksli {% url %} — CLAUDE.md gotcha #12)
   sakratmasdan tortiladi: yangi kadrlar img.decode() dan KEYIN, birin-ketin
   fade-up bo'lib qo'shiladi; tugma joyi min-height bilan band — UI sakramaydi.
   Oxirgi sahifadan keyin tugma yumshoq yo'qoladi, hisoblagich qoladi. */
(function () {
  var wall = document.getElementById("gallery-wall");
  var moreBtn = document.getElementById("gw-more");
  if (!wall || !moreBtn) return;

  var FEED_URL = wall.dataset.feedUrl;
  var shownEl = document.getElementById("gw-shown");
  var nextPage = 2;
  var loading = false;

  function makeItem(img) {
    var fig = document.createElement("figure");
    fig.className = "gw-item";
    fig.style.setProperty("--ar", img.ar || "1.5");
    fig.tabIndex = 0;

    var im = document.createElement("img");
    im.src = img.url;
    im.alt = img.hint || "";
    // eager: dinamik kadrlar hozir ko'rsatiladi; lazy'da decode() hech settle bo'lmaydi
    im.loading = "eager";
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
    // O'rin band qolaveradi (.gw-more-wrap min-height) — layout sakramaydi
    setTimeout(function () {
      moreBtn.hidden = true;
    }, 450);
  }

  moreBtn.addEventListener("click", function () {
    if (loading) return;
    loading = true;
    setBtn(moreBtn.dataset.labelLoading, true);

    fetch(FEED_URL + "?page=" + nextPage, {
      headers: { "Accept-Language": document.documentElement.lang || "xo" },
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var items = (data.images || []).map(makeItem);
        items.forEach(function (fig) {
          wall.appendChild(fig);
        });

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
        if (!data.has_next) finish();
      })
      .catch(function (err) {
        console.error("Gallery feed failed", err);
        setBtn(moreBtn.dataset.labelRetry, false);
      })
      .finally(function () {
        loading = false;
      });
  });
})();
