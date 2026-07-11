/* JK-DinAdmin theme bootstrap — runs before paint.
   XIVA INK v4 is a single universal dark-ink scheme: force Unfold's
   `adminTheme` to 'dark' so its own widgets (selects, datepickers,
   tables) follow the same palette as editorial.css. No toggle. */
(function () {
    try {
        localStorage.setItem('adminTheme', '"dark"');
        var r = document.documentElement;
        r.classList.add('dark');
        r.setAttribute('data-theme', 'dark');
    } catch (e) {
        /* ignore */
    }
})();
