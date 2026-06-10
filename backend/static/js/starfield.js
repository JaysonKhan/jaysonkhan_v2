/* starfield.js — "Xiva yulduz turkumi" scroll-morph foni (XIVA INK v4)
   Yulduzlar (canvas zarralari) Ichan-Qal'a obidalarini chizadi; scroll bilan
   bir obidadan ikkinchisiga yulduzlar harakati orqali kino kabi o'tadi.
   Vanilla port of the design prototype's starfield.jsx (docs/starfield-implementation.md §8).
   Config (optional, read every frame):
     window.XIVA_STARFIELD = { intensity: 0..1, lines: true|false }
*/
(function () {
  var SF_GRID = 640;

  /* ── kichik yordamchilar ── */
  function sfClamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function sfEase(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }
  function sfHash(i) {
    var x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
  }

  /* ── chizish yordamchilari (640×640 fazoda) ── */
  function ln(g, x1, y1, x2, y2) {
    g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
  }
  function band(g, cx, y, hw, sag) {
    g.beginPath(); g.moveTo(cx - hw, y);
    g.quadraticCurveTo(cx, y + sag, cx + hw, y); g.stroke();
  }
  function ringEllipse(g, cx, cy, rx, ry) {
    g.beginPath(); g.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2); g.stroke();
  }
  // uchli (islimiy) ravoq
  function arch(g, cx, baseY, hw, apexY) {
    var springY = apexY + hw * 1.15;
    g.beginPath();
    g.moveTo(cx - hw, baseY);
    g.lineTo(cx - hw, springY);
    g.quadraticCurveTo(cx - hw * 0.92, apexY + (springY - apexY) * 0.18, cx, apexY);
    g.quadraticCurveTo(cx + hw * 0.92, apexY + (springY - apexY) * 0.18, cx + hw, springY);
    g.lineTo(cx + hw, baseY);
    g.stroke();
  }
  // gumbaz (yuqori yarim ellips)
  function dome(g, cx, baseY, rx, ry) {
    g.beginPath(); g.ellipse(cx, baseY, rx, ry, 0, Math.PI, Math.PI * 2, false); g.stroke();
  }
  function dots(g, n, fx) {
    for (var i = 0; i < n; i++) {
      var p = fx();
      if (p) g.fillRect(p[0], p[1], 2.3, 2.3);
    }
  }
  function teeth(g, x1, x2, y, w, h, gap) {
    for (var x = x1; x + w <= x2; x += w + gap) {
      g.strokeRect(x, y - h, w, h);
    }
  }

  /* ── 1. Kalta Minor ── */
  function drawKalta(g) {
    ln(g, 70, 595, 575, 595);
    var bx = 320, yb = 590, yt = 130, bw = 158, tw = 100;
    ln(g, bx - bw, yb, bx - tw, yt);
    ln(g, bx + bw, yb, bx + tw, yt);
    ringEllipse(g, bx, yt, tw, 15);
    [0.07, 0.16, 0.27, 0.34, 0.47, 0.55, 0.7, 0.8, 0.92].forEach(function (f) {
      var y = yt + (yb - yt) * f;
      var hw = tw + (bw - tw) * f;
      band(g, bx, y, hw, 6 + 12 * f);
      if (f === 0.16 || f === 0.55) band(g, bx, y + 9, hw + 1.5, 6 + 12 * f);
    });
    // koshin nuqtalari
    dots(g, 150, function () {
      var f = 0.1 + Math.random() * 0.8;
      var y = yt + (yb - yt) * f;
      var hw = (tw + (bw - tw) * f) * 0.92;
      return [bx + (Math.random() * 2 - 1) * hw, y + (Math.random() - 0.5) * 14];
    });
    // o'ng past devor
    ln(g, 492, 595, 492, 545);
    ln(g, 492, 545, 575, 545);
    teeth(g, 498, 575, 545, 12, 12, 9);
  }

  /* ── 2. Madrasa peshtog'i ── */
  function drawPortal(g) {
    ln(g, 60, 595, 580, 595);
    // markaziy pilon
    g.strokeRect(225, 112, 190, 483);
    g.strokeRect(243, 132, 154, 463);
    // xattotlik bandi
    ln(g, 243, 180, 397, 180);
    ln(g, 243, 202, 397, 202);
    // katta uchli ravoq + ichki ravoq
    arch(g, 320, 595, 58, 252);
    arch(g, 320, 595, 43, 282);
    // qanotlar
    ln(g, 60, 400, 225, 400);
    ln(g, 415, 400, 580, 400);
    ln(g, 60, 400, 60, 595);
    ln(g, 580, 400, 580, 595);
    [102, 165].forEach(function (cx) { arch(g, cx, 595, 23, 455); });
    [472, 538].forEach(function (cx) { arch(g, cx, 595, 23, 455); });
    // chap gumbaz
    dome(g, 132, 400, 52, 58);
    ln(g, 132, 342, 132, 322);
    ringEllipse(g, 132, 318, 3.5, 3.5);
    // pilon naqsh nuqtalari
    dots(g, 70, function () {
      var x = 250 + Math.random() * 140;
      var y = 220 + Math.random() * 120;
      return [x, y];
    });
  }

  /* ── 3. Islom Xo'ja minorasi ── */
  function drawIslomXoja(g) {
    ln(g, 70, 595, 575, 595);
    var cx = 215, yb = 590, yt = 122, bw = 46, tw = 17;
    ln(g, cx - bw, yb, cx - tw, yt);
    ln(g, cx + bw, yb, cx + tw, yt);
    [0.08, 0.2, 0.32, 0.44, 0.56, 0.68, 0.8, 0.9].forEach(function (f) {
      var y = yt + (yb - yt) * f;
      var hw = tw + (bw - tw) * f;
      band(g, cx, y, hw, 4 + 6 * f);
    });
    // fonar + qubba
    g.strokeRect(cx - 25, 86, 50, 36);
    ln(g, cx - 9, 92, cx - 9, 116);
    ln(g, cx, 92, cx, 116);
    ln(g, cx + 9, 92, cx + 9, 116);
    dome(g, cx, 86, 27, 30);
    ln(g, cx, 56, cx, 38);
    ringEllipse(g, cx, 34, 3.5, 3.5);
    // o'ngda maqbara: poydevor + baraban + gumbaz
    g.strokeRect(350, 482, 235, 108);
    [392, 442, 497, 547].forEach(function (ax) { arch(g, ax, 590, 18, 520); });
    ln(g, 415, 482, 415, 440);
    ln(g, 530, 482, 530, 440);
    band(g, 472, 440, 58, 5);
    dome(g, 472, 440, 80, 92);
    ln(g, 472, 348, 472, 324);
    ringEllipse(g, 472, 319, 4, 4);
  }

  /* ── 4. Xiva silueti ── */
  function drawSkyline(g) {
    ln(g, 40, 595, 600, 595);
    // qal'a devorlari
    ln(g, 40, 502, 152, 502); ln(g, 40, 502, 40, 595);
    teeth(g, 46, 150, 502, 13, 13, 10);
    ln(g, 478, 508, 600, 508); ln(g, 600, 508, 600, 595);
    teeth(g, 484, 598, 508, 13, 13, 10);
    // chap ingichka minora
    var mx = 110, myb = 502, myt = 162;
    ln(g, mx - 20, myb, mx - 9, myt);
    ln(g, mx + 20, myb, mx + 9, myt);
    [0.15, 0.35, 0.55, 0.75].forEach(function (f) {
      var y = myt + (myb - myt) * f;
      band(g, mx, y, 9 + 11 * f, 4);
    });
    dome(g, mx, 162, 13, 15);
    ln(g, mx, 147, mx, 134);
    ringEllipse(g, mx, 130, 3, 3);
    // markaziy maqbara: portal + baraban + katta gumbaz
    g.strokeRect(230, 470, 160, 125);
    arch(g, 310, 595, 34, 503);
    ln(g, 265, 470, 265, 432);
    ln(g, 355, 470, 355, 432);
    band(g, 310, 432, 45, 4);
    dome(g, 310, 432, 72, 82);
    ln(g, 310, 350, 310, 328);
    ringEllipse(g, 310, 323, 4, 4);
    // kichik gumbazlar
    ln(g, 178, 540, 178, 502); ln(g, 232, 540, 232, 502);
    dome(g, 205, 502, 30, 33);
    ln(g, 405, 545, 405, 510); ln(g, 455, 545, 455, 510);
    dome(g, 430, 510, 26, 29);
    // o'ngda Kalta Minor "dumi"
    var kx = 540, kyb = 595, kyt = 362;
    ln(g, kx - 48, kyb, kx - 35, kyt);
    ln(g, kx + 48, kyb, kx + 35, kyt);
    ringEllipse(g, kx, kyt, 35, 7);
    [0.28, 0.55, 0.8].forEach(function (f) {
      var y = kyt + (kyb - kyt) * f;
      band(g, kx, y, 35 + 13 * f, 5);
    });
  }

  /* ── nuqta tanlash: chizilgan rasmni piksel sifatida o'qib olish ── */
  function sortByAngle(pts, count) {
    var cx = 0, cy = 0, i;
    for (i = 0; i < count; i++) { cx += pts[i * 2]; cy += pts[i * 2 + 1]; }
    cx /= count; cy /= count;
    var idx = [];
    for (i = 0; i < count; i++) idx.push(i);
    idx.sort(function (a, b) {
      return Math.atan2(pts[a * 2 + 1] - cy, pts[a * 2] - cx) -
        Math.atan2(pts[b * 2 + 1] - cy, pts[b * 2] - cx);
    });
    var out = new Float32Array(count * 2);
    idx.forEach(function (src, dst) {
      out[dst * 2] = pts[src * 2];
      out[dst * 2 + 1] = pts[src * 2 + 1];
    });
    return out;
  }

  function sampleShape(drawFn, count) {
    var c = document.createElement("canvas");
    c.width = SF_GRID; c.height = SF_GRID;
    var g = c.getContext("2d", { willReadFrequently: true });
    g.strokeStyle = "#fff"; g.fillStyle = "#fff";
    g.lineWidth = 3.4; g.lineCap = "round"; g.lineJoin = "round";
    drawFn(g);
    var data = g.getImageData(0, 0, SF_GRID, SF_GRID).data;
    var px = [];
    for (var y = 0; y < SF_GRID; y += 2) {
      for (var x = 0; x < SF_GRID; x += 2) {
        if (data[(y * SF_GRID + x) * 4 + 3] > 90) px.push(x, y);
      }
    }
    var n = px.length / 2;
    var pts = new Float32Array(count * 2);
    for (var i = 0; i < count; i++) {
      var j = (Math.random() * n) | 0;
      pts[i * 2] = px[j * 2] / SF_GRID + (Math.random() - 0.5) * 0.005;
      pts[i * 2 + 1] = px[j * 2 + 1] / SF_GRID + (Math.random() - 0.5) * 0.005;
    }
    return sortByAngle(pts, count);
  }

  /* ── 5. Galaktika spirali (yakuniy shakl) ── */
  function galaxyPoints(count) {
    var pts = new Float32Array(count * 2);
    for (var i = 0; i < count; i++) {
      if (i % 8 === 0) {
        // markaziy yadro
        var a = Math.random() * Math.PI * 2;
        var r = Math.pow(Math.random(), 2) * 0.07;
        pts[i * 2] = 0.5 + Math.cos(a) * r * 1.3;
        pts[i * 2 + 1] = 0.5 + Math.sin(a) * r;
      } else {
        var armN = 3;
        var arm = i % armN;
        var t = Math.pow(Math.random(), 0.62);
        var ang = arm * ((Math.PI * 2) / armN) + t * 4.3 +
          (Math.random() - 0.5) * 0.6 * (1.25 - t);
        var rr = 0.045 + t * 0.42;
        pts[i * 2] = 0.5 + Math.cos(ang) * rr * 1.14;
        pts[i * 2 + 1] = 0.5 + Math.sin(ang) * rr * 0.8;
      }
    }
    return sortByAngle(pts, count);
  }

  var SF_NAMES = [
    "KALTA MINOR · ICHAN QAL’A",
    "MADRASA PESHTOG‘I · XIVA",
    "ISLOM XO‘JA MINORASI",
    "XIVA SILUETI",
    "TUNGI OSMON · GALAKTIKA",
  ];

  /* ── yulduz spraytlari (yorqin yadro + keng nur halosi) ── */
  function makeSprite(core, halo, faint) {
    var c = document.createElement("canvas");
    c.width = 64; c.height = 64;
    var g = c.getContext("2d");
    var rg = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    rg.addColorStop(0, core);
    rg.addColorStop(0.2, halo);
    rg.addColorStop(0.5, faint);
    rg.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = rg;
    g.fillRect(0, 0, 64, 64);
    return c;
  }

  /* ── init: canvas yaratish + render sikli ── */
  function init() {
    var canvas = document.createElement("canvas");
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.cssText =
      "position:fixed;inset:0;width:100%;height:100%;" +
      "z-index:0;pointer-events:none;display:block;";
    document.body.prepend(canvas);

    var ctx = canvas.getContext("2d");
    var rm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var mobile = window.innerWidth < 768;
    var N = mobile ? 820 : 1800;

    var SHAPES = [
      sampleShape(drawKalta, N),
      sampleShape(drawPortal, N),
      sampleShape(drawIslomXoja, N),
      sampleShape(drawSkyline, N),
      galaxyPoints(N),
    ];

    // ranglar: krem (asosiy), feruza, terrakota
    var sprites = [
      makeSprite("rgba(255,255,250,1)", "rgba(255,248,228,0.68)", "rgba(238,232,214,0.18)"),
      makeSprite("rgba(240,255,252,1)", "rgba(140,235,220,0.72)", "rgba(118,214,200,0.2)"),
      makeSprite("rgba(255,248,240,1)", "rgba(255,176,126,0.72)", "rgba(233,148,106,0.2)"),
    ];
    var coreCols = [
      "rgba(255,253,244,", "rgba(196,255,245,", "rgba(255,210,178,",
    ];
    var strokeCols = [
      "rgba(238,232,214,", "rgba(118,214,200,", "rgba(233,148,106,",
    ];

    // zarralar
    var P = new Array(N);
    for (var i = 0; i < N; i++) {
      var h0 = sfHash(i), h1 = sfHash(i + 9000), h2 = sfHash(i + 21000);
      P[i] = {
        x: 0, y: 0, px: 0, py: 0, init: false,
        h0: h0, h1: h1,
        c: h2 < 0.84 ? 0 : h2 < 0.93 ? 1 : 2,
        r: 1.0 + h1 * 1.9 + (h0 > 0.96 ? 2.0 : 0),
        spd: 0.7 + h0 * 0.9,
        ph: h1 * Math.PI * 2,
      };
    }

    // orqa fon changi (mayda statik yulduzlar, parallaks bilan)
    var DUST = mobile ? 110 : 240;
    var dust = new Array(DUST);
    for (var di = 0; di < DUST; di++) {
      dust[di] = {
        x: Math.random(), y: Math.random(),
        z: 0.25 + Math.random() * 0.75,
        r: 0.5 + Math.random() * 1.1,
        ph: Math.random() * Math.PI * 2,
      };
    }

    // uchar yulduz
    var meteor = null, meteorAt = performance.now() + 3500 + Math.random() * 4000;

    var vw = 0, vh = 0, dpr = 1;
    function resize() {
      vw = window.innerWidth; vh = window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = vw * dpr; canvas.height = vh * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    var sp = { cur: 0, target: 0 };
    var anchorStep = Math.max(1, Math.ceil(N / 120));

    function proj(nx, ny) {
      var s = Math.min(Math.min(vw, vh * 1.06) * 0.94, 880);
      var cx = vw > 1024 ? vw * 0.60 : vw * 0.5;
      var cy = vh * 0.52;
      return [cx + (nx - 0.5) * s, cy + (ny - 0.55) * s];
    }

    function frame(ts) {
      requestAnimationFrame(frame);
      var CFG = window.XIVA_STARFIELD || {};
      var inten = sfClamp(CFG.intensity == null ? 1 : CFG.intensity, 0, 1);
      var wantLines = CFG.lines !== false;
      ctx.clearRect(0, 0, vw, vh);
      if (inten <= 0.01) return;

      // scroll → shakl pozitsiyasi
      var doc = document.documentElement;
      var maxScroll = Math.max(1, doc.scrollHeight - vh);
      sp.target = (window.scrollY / maxScroll) * (SHAPES.length - 1);
      sp.cur += (sp.target - sp.cur) * (rm ? 1 : 0.065);

      var i0 = sfClamp(Math.floor(sp.cur), 0, SHAPES.length - 1);
      var i1 = Math.min(i0 + 1, SHAPES.length - 1);
      var f = sfClamp(sp.cur - i0, 0, 1);
      var A = SHAPES[i0], B = SHAPES[i1];

      // ── chang qatlami ──
      ctx.globalCompositeOperation = "source-over";
      var scrY = window.scrollY;
      for (var d = 0; d < DUST; d++) {
        var du = dust[d];
        var y = (du.y * vh - scrY * 0.045 * du.z) % vh;
        if (y < 0) y += vh;
        var dtw = rm ? 0.8 : 0.62 + 0.38 * Math.sin(ts * 0.0008 * du.z + du.ph);
        ctx.globalAlpha = 0.5 * du.z * dtw * inten;
        ctx.fillStyle = "#eee8d6";
        ctx.fillRect(du.x * vw, y, du.r, du.r);
      }

      // ── asosiy yulduzlar ──
      var k = rm ? 1 : 0.085;
      ctx.globalCompositeOperation = "lighter";
      var speedSum = 0, speedCnt = 0;
      for (var n = 0; n < N; n++) {
        var p = P[n];
        var j = n * 2;
        var st = p.h0 * 0.35;
        var ff = sfClamp((f - st) / 0.65, 0, 1);
        var e = sfEase(ff);
        var ax = A[j], ay = A[j + 1];
        var nx = ax + (B[j] - ax) * e;
        var ny = ay + (B[j + 1] - ay) * e;
        // yoy bo'ylab uchish (galaktik burilish)
        if (!rm && f > 0.001 && f < 0.999) {
          var dxs = B[j] - ax, dys = B[j + 1] - ay;
          var arcv = Math.sin(e * Math.PI) * (p.h1 - 0.5) * 0.22;
          nx += -dys * arcv; ny += dxs * arcv;
        }
        var pr = proj(nx, ny);
        var tx = pr[0], ty = pr[1];
        if (!rm) {
          tx += Math.sin(ts * 0.00037 * p.spd + p.ph) * 2.6;
          ty += Math.cos(ts * 0.00031 * p.spd + p.ph * 1.7) * 2.6;
        }
        if (!p.init) { p.x = tx; p.y = ty + 40; p.init = true; }
        p.px = p.x; p.py = p.y;
        p.x += (tx - p.x) * k;
        p.y += (ty - p.y) * k;
        var dx = p.x - p.px, dy = p.y - p.py;
        var spd = Math.abs(dx) + Math.abs(dy);
        if (n % anchorStep === 0) { speedSum += spd; speedCnt++; }

        var tw = rm ? 0.9 : 0.78 + 0.22 * Math.sin(ts * 0.0012 * p.spd + p.ph);
        var glint = rm ? 0 : Math.pow(Math.max(0, Math.sin(ts * 0.00043 * p.spd + p.ph * 3.7)), 28);
        var a = sfClamp((tw + glint * 0.7) * inten, 0, 1);
        if (!rm && spd > 1.6) {
          // harakat chizig'i — yulduz "oqib o'tayotgan" effekt
          ctx.globalAlpha = sfClamp(a * 0.9, 0, 1);
          ctx.strokeStyle = strokeCols[p.c] + "0.9)";
          ctx.lineWidth = sfClamp(p.r * 0.75, 0.7, 1.8);
          ctx.beginPath();
          ctx.moveTo(p.x - dx * 3.4, p.y - dy * 3.4);
          ctx.lineTo(p.x, p.y);
          ctx.stroke();
        }
        // yorqin halo
        ctx.globalAlpha = a * 0.85;
        var sz = p.r * (6.4 + glint * 6.5);
        ctx.drawImage(sprites[p.c], p.x - sz / 2, p.y - sz / 2, sz, sz);
        // o'tkir yadro
        ctx.globalAlpha = a;
        ctx.fillStyle = coreCols[p.c] + "1)";
        ctx.beginPath();
        ctx.arc(p.x, p.y, Math.max(p.r * 0.62, 0.65) + glint * 1.0, 0, Math.PI * 2);
        ctx.fill();
        // diffraksiya nurlari (yirik yoki chaqnayotgan yulduzlar)
        if (p.r > 2.2 || glint > 0.45) {
          var sl = p.r * 4.0 + glint * 11;
          ctx.globalAlpha = a * 0.55;
          ctx.strokeStyle = coreCols[p.c] + "0.9)";
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(p.x - sl, p.y); ctx.lineTo(p.x + sl, p.y);
          ctx.moveTo(p.x, p.y - sl); ctx.lineTo(p.x, p.y + sl);
          ctx.stroke();
        }
      }
      var avgSpd = speedCnt ? speedSum / speedCnt : 0;
      var settle = sfClamp(1 - avgSpd / 2.2, 0, 1);

      // ── turkum chiziqlari (yulduzlar orasidagi ingichka iplar) ──
      if (wantLines && settle > 0.15) {
        ctx.globalCompositeOperation = "source-over";
        var dmax = Math.min(vw, vh) * 0.05;
        ctx.lineWidth = 0.8;
        for (var ii = 0; ii < N; ii += anchorStep) {
          var p1 = P[ii];
          for (var q = ii + anchorStep; q < N; q += anchorStep) {
            var p2 = P[q];
            var ddx = p1.x - p2.x, ddy = p1.y - p2.y;
            if (Math.abs(ddx) > dmax || Math.abs(ddy) > dmax) continue;
            var dd = Math.sqrt(ddx * ddx + ddy * ddy);
            if (dd < dmax) {
              ctx.globalAlpha = (1 - dd / dmax) * 0.24 * inten * settle;
              ctx.strokeStyle = "#eee8d6";
              ctx.beginPath();
              ctx.moveTo(p1.x, p1.y);
              ctx.lineTo(p2.x, p2.y);
              ctx.stroke();
            }
          }
        }
      }

      // ── uchar yulduz ──
      if (!rm) {
        if (!meteor && ts > meteorAt) {
          var fromLeft = Math.random() > 0.5;
          meteor = {
            x: fromLeft ? -40 : vw + 40,
            y: vh * (0.06 + Math.random() * 0.3),
            vx: (fromLeft ? 1 : -1) * (7 + Math.random() * 5),
            vy: 2.2 + Math.random() * 1.6,
            life: 1,
          };
        }
        if (meteor) {
          meteor.x += meteor.vx; meteor.y += meteor.vy;
          meteor.life -= 0.008;
          ctx.globalCompositeOperation = "lighter";
          ctx.globalAlpha = sfClamp(meteor.life, 0, 1) * 0.95 * inten;
          var gr = ctx.createLinearGradient(
            meteor.x - meteor.vx * 11, meteor.y - meteor.vy * 11, meteor.x, meteor.y);
          gr.addColorStop(0, "rgba(238,232,214,0)");
          gr.addColorStop(1, "rgba(255,255,250,1)");
          ctx.strokeStyle = gr; ctx.lineWidth = 1.8;
          ctx.beginPath();
          ctx.moveTo(meteor.x - meteor.vx * 11, meteor.y - meteor.vy * 11);
          ctx.lineTo(meteor.x, meteor.y);
          ctx.stroke();
          // bosh nuri
          ctx.drawImage(sprites[0], meteor.x - 9, meteor.y - 9, 18, 18);
          if (meteor.life <= 0 || meteor.x < -80 || meteor.x > vw + 80 || meteor.y > vh + 80) {
            meteor = null;
            meteorAt = ts + 4500 + Math.random() * 6000;
          }
        }
      }

      // ── obida nomi (juda nozik sarlavha) ──
      var near = Math.round(sp.cur);
      var capA = sfClamp(1 - Math.abs(sp.cur - near) * 2.4, 0, 1) * 0.5 * inten * settle;
      if (capA > 0.03) {
        ctx.globalCompositeOperation = "source-over";
        ctx.globalAlpha = capA;
        ctx.fillStyle = "#a89f8a";
        ctx.font = "10.5px 'IBM Plex Mono', monospace";
        try { ctx.letterSpacing = "3px"; } catch (e) {}
        ctx.textAlign = "right";
        ctx.fillText(SF_NAMES[near], vw - 26, vh - 26);
        try { ctx.letterSpacing = "0px"; } catch (e) {}
      }
      ctx.globalAlpha = 1;
    }
    requestAnimationFrame(frame);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
