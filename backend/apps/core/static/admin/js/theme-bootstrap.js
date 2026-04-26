/* JK-DinAdmin theme bootstrap — runs before paint.
   1. Default Unfold's `adminTheme` to `'light'` if user hasn't picked yet
      (otherwise `auto` follows system pref → unwanted dark mode).
   2. Sync with our `jk-tweaks.theme` (used on login + public site) so
      toggling in one place affects the other.
*/
(function() {
    try {
        var unfoldKey = 'adminTheme';
        var ourKey = 'jk-tweaks';

        var unfoldTheme = localStorage.getItem(unfoldKey);
        var ourTweaks = {};
        try { ourTweaks = JSON.parse(localStorage.getItem(ourKey) || '{}'); } catch (e) {}

        // If our theme is explicitly set, push it to Unfold
        if (ourTweaks.theme && ourTweaks.theme !== unfoldTheme) {
            localStorage.setItem(unfoldKey, '"' + ourTweaks.theme + '"');
            unfoldTheme = '"' + ourTweaks.theme + '"';
        }

        // Default to light if neither is set
        if (!unfoldTheme || unfoldTheme === '"auto"') {
            localStorage.setItem(unfoldKey, '"light"');
            unfoldTheme = '"light"';
        }

        // Apply class to <html> immediately to avoid FOUC
        var theme = unfoldTheme.replace(/"/g, '');
        var r = document.documentElement;
        if (theme === 'dark') {
            r.classList.add('dark');
            r.setAttribute('data-theme', 'dark');
        } else {
            r.classList.remove('dark');
            r.setAttribute('data-theme', 'light');
        }

        // Mirror to ourKey if missing
        if (!ourTweaks.theme) {
            ourTweaks.theme = theme;
            try { localStorage.setItem(ourKey, JSON.stringify(ourTweaks)); } catch (e) {}
        }
    } catch (e) {
        /* ignore */
    }
})();
