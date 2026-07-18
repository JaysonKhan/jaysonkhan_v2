/* orbit.js — "Quyosh sistemasi" mehmonlar orbitasi (kontakt sahifasi).
   Markazda egasi (quyosh), atrofida saytga Telegram orqali kirgan mehmonlar
   sayyoralardek aylanadi; rasmsiz mehmonlar — sayyoralarning yo'ldoshlari.
   Pseudo-3D: ellips trayektoriya + masofaga qarab scale/z-index/xiralik.
   Unumdorlik: bitta rAF, faqat transform/opacity (composited), seksiya
   ekrandan chiqsa IntersectionObserver to'xtatadi; reduced-motion'da statik.
   Bosilganda — hech qayerga navigatsiya qilinmaydi (privacy policy: 3-shaxs
   saytiga yo'naltirmaymiz). Ism pastdagi izohda ko'rsatiladi, orbita davom
   etadi; bir necha soniyadan keyin standart matnga qaytadi. */
(function () {
  var stage = document.getElementById("orbit-stage");
  if (!stage) return;

  var note = document.getElementById("orbit-note");
  var defaultNote = note
    ? note.getAttribute("data-default") || note.textContent
    : "";
  var revealTimer = null;
  var revealedEl = null;

  function reveal(el) {
    var name = el.getAttribute("title");
    if (!name || !note) return;
    if (revealedEl) revealedEl.classList.remove("is-revealed");
    revealedEl = el;
    el.classList.add("is-revealed");
    note.textContent = name;
    note.classList.add("orbit-note--revealed");
    clearTimeout(revealTimer);
    revealTimer = setTimeout(function () {
      note.textContent = defaultNote;
      note.classList.remove("orbit-note--revealed");
      if (revealedEl) revealedEl.classList.remove("is-revealed");
      revealedEl = null;
    }, 3200);
  }

  stage.addEventListener("click", function (e) {
    var el = e.target.closest(".orbit-planet, .orbit-moon");
    if (el) reveal(el);
  });

  var planets = [].slice.call(stage.querySelectorAll(".orbit-planet"));
  var moons = [].slice.call(stage.querySelectorAll(".orbit-moon"));
  if (!planets.length) return;

  var rm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SQUASH = 0.42; // orbital tekislik qiyaligi (ellips)
  var GOLDEN = 2.39996; // boshlang'ich fazalarni tekis taqsimlash

  function hash(i) {
    var x = Math.sin(i * 91.7 + 47.3) * 24634.5453;
    return x - Math.floor(x);
  }

  // Har sayyoraga ring/tezlik/faza biriktirish (deterministik)
  var conf = planets.map(function (el, i) {
    var ring = i % 3;
    return {
      el: el,
      ring: ring,
      // tashqi ringlar sekinroq (Kepler kayfiyati), har biriga ozgina farq
      speed: (0.34 - ring * 0.09) * (0.8 + hash(i) * 0.5),
      dir: ring === 1 ? -1 : 1, // o'rta ring teskari aylanadi
      phase: i * GOLDEN,
      moons: [],
    };
  });

  // Yo'ldoshlarni sayyoralarga taqsimlash
  moons.forEach(function (el, i) {
    var host = conf[i % conf.length];
    host.moons.push({
      el: el,
      speed: 1.6 + hash(i + 50) * 1.2,
      dir: i % 2 ? -1 : 1,
      phase: hash(i + 99) * Math.PI * 2,
    });
  });

  var W = 0,
    RADII = [0, 0, 0];
  function resize() {
    W = stage.clientWidth;
    RADII = [W * 0.21, W * 0.325, W * 0.44];
  }
  resize();
  window.addEventListener("resize", resize);

  function place(t) {
    // Sahna hali o'lchamsiz bo'lsa (yashirin tab/panel) — qayta o'lchash
    if (W < 50) {
      resize();
      if (W < 50) return;
    }
    for (var i = 0; i < conf.length; i++) {
      var c = conf[i];
      var a = c.phase + t * c.speed * c.dir;
      var cs = Math.cos(a),
        sn = Math.sin(a);
      var x = cs * RADII[c.ring];
      var y = sn * RADII[c.ring] * SQUASH;
      // sn > 0 — oldinda (kattaroq/ravshanroq), sn < 0 — quyosh ortida
      var depth = (sn + 1) / 2; // 0..1
      var sc = 0.78 + depth * 0.38;
      c.el.style.transform =
        "translate(-50%, -50%) translate3d(" +
        x.toFixed(1) +
        "px," +
        y.toFixed(1) +
        "px,0) scale(" +
        sc.toFixed(3) +
        ")";
      c.el.style.zIndex = sn > 0 ? 30 : 10;
      c.el.style.opacity = (0.62 + depth * 0.38).toFixed(3);

      for (var m = 0; m < c.moons.length; m++) {
        var mo = c.moons[m];
        var ma = mo.phase + t * mo.speed * mo.dir;
        var mr = 0.52; // sayyora radiusiga nisbatan (em orqali CSSda)
        var mx = x + Math.cos(ma) * (RADII[0] * mr * 0.55);
        var my = y + Math.sin(ma) * (RADII[0] * mr * 0.55) * SQUASH;
        var msc = sc * 0.9;
        mo.el.style.transform =
          "translate(-50%, -50%) translate3d(" +
          mx.toFixed(1) +
          "px," +
          my.toFixed(1) +
          "px,0) scale(" +
          msc.toFixed(3) +
          ")";
        mo.el.style.zIndex = Math.sin(ma) > 0 ? 31 : 9;
        mo.el.style.opacity = (0.55 + depth * 0.45).toFixed(3);
      }
    }
  }

  if (rm) {
    place(1.7); // statik, tarqoq joylashuv
    return;
  }

  var running = true;
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(
      function (entries) {
        running = entries[0].isIntersecting;
      },
      { rootMargin: "80px" },
    ).observe(stage);
  }

  var start = performance.now();
  (function frame(ts) {
    requestAnimationFrame(frame);
    if (!running) return;
    place((ts - start) / 1000);
  })(start);
})();
