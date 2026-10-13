/*
 * Theme toggle wiring: flips the footer light/dark entry, persists the
 * viewer's choice in localStorage ('aurora-theme': 'light'|'dark') and
 * reloads so ApexCharts and the live aurora module re-render in the new
 * theme (charts bake their theme at creation). The pre-paint resolver at
 * the top of header.inc re-applies the saved choice on every page load;
 * js.inc's theme_mode honours it too, so charts render correctly from
 * the first paint after the reload. The body theme class remains the
 * single source of truth for styling. Element-guarded: pages without
 * #theme-toggle are a no-op.
 */
(function () {
    'use strict';

    var THEME_KEY = 'aurora-theme';
    var THEME_CLASSES = ['auto-theme', 'light-theme', 'dark-theme'];

    function savedTheme() {
        try {
            var v = localStorage.getItem(THEME_KEY);
            return (v === 'light' || v === 'dark') ? v : null;
        } catch (e) {
            return null;
        }
    }

    // Effective theme: saved override first, else the body class baked
    // at build time ('auto' resolves against the OS preference).
    function currentTheme() {
        var saved = savedTheme();
        if (saved) {
            return saved;
        }
        if (document.body.classList.contains('dark-theme')) {
            return 'dark';
        }
        if (document.body.classList.contains('auto-theme') &&
            window.matchMedia &&
            window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    // The label announces the theme the click switches TO.
    function switchLabel(theme) {
        return theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    }

    function applyTheme(body, theme) {
        THEME_CLASSES.forEach(function (cls) {
            body.classList.remove(cls);
        });
        body.classList.add(theme + '-theme');
    }

    function boot() {
        var button = document.getElementById('theme-toggle');
        if (!button) {
            return;
        }
        button.setAttribute('aria-label', switchLabel(currentTheme()));
        button.setAttribute('title', switchLabel(currentTheme()));
        button.addEventListener('click', function (evt) {
            // The entry is an <a role="button">: suppress the default
            // jump-to-top/# behavior. We reload or re-skin instead.
            evt.preventDefault();
            var next = currentTheme() === 'dark' ? 'light' : 'dark';
            var persisted = true;
            try {
                localStorage.setItem(THEME_KEY, next);
            } catch (e) {
                // Storage unavailable (e.g. private mode): swap the classes
                // for this page only; reloading would lose the choice.
                persisted = false;
            }
            applyTheme(document.body, next);
            if (persisted) {
                window.location.reload();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
