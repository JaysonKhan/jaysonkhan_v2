/* Presentation only: no requests, mail mutations, HTML parsing, or third-party assets. */
(function () {
  'use strict';
  if (!window.rcmail) return;
  // XIVA INK is the first-visit default. Native controls continue to own the
  // explicit Paper preference and iframe propagation; never reset a choice.
  if (window.parent === window && rcmail.env.jaysonkhan_mail_brand
      && rcmail.get_cookie && !rcmail.get_cookie('colorMode')) {
    rcmail.set_cookie('colorMode', 'dark', false);
    document.documentElement.classList.add('dark-mode');
  }
  rcmail.addEventListener('init', function () {
    if (!rcmail.env.jaysonkhan_mail_brand) return;
    document.body.classList.add('jaysonkhan-mail');
    var logo = document.querySelector('#logo');
    if (logo) logo.alt = 'JaysonKhan Mail';
    // Upstream hides inner labels on narrow layouts. Keep their accessible
    // names, including split-button options; never derive labels from mail HTML.
    document.querySelectorAll('a.button.icon, .menu a, #compose-headers a.icon').forEach(function (button) {
      // The theme toggle's visible label changes at runtime; retain its native
      // accessible text instead of freezing an aria-label to the initial mode.
      if (button.classList.contains('theme')) return;
      var label = button.querySelector('.inner');
      if (!button.hasAttribute('aria-label') && label && label.textContent.trim()) {
        button.setAttribute('aria-label', label.textContent.trim());
      }
    });
    // Elastic creates its narrow-screen overflow buttons later in the same
    // init dispatch. Label that generated chrome after dispatch, no mail scan.
    window.requestAnimationFrame(function () {
      document.querySelectorAll('.header a.toolbar-menu-button, .header a.toolbar-list-button').forEach(function (button) {
        button.setAttribute('aria-label', rcmail.gettext('options'));
      });
      document.querySelectorAll('.floating-action-buttons a').forEach(function (button) {
        var label = button.querySelector('.inner');
        if (label && label.textContent.trim()) button.setAttribute('aria-label', label.textContent.trim());
      });
    });
    var t = function (key) { return rcmail.gettext(key, 'jaysonkhan_mail'); };
    function element(tag, className, text) {
      var el = document.createElement(tag);
      if (className) el.className = className;
      if (text) el.textContent = text;
      return el;
    }
    var login = document.querySelector('#login-form');
    if (login) {
      ['rcmloginuser', 'rcmloginpwd'].forEach(function (id) {
        var field = document.getElementById(id);
        if (field) {
          var label = document.querySelector('label[for="' + id + '"]');
          field.setAttribute('aria-label', field.placeholder || (label && label.textContent.trim()) || (id === 'rcmloginuser' ? 'Username' : 'Password'));
          field.autocomplete = id === 'rcmloginuser' ? 'username' : 'current-password';
        }
      });
      var intro = element('div', 'jk-mail-intro');
      intro.append(element('span', 'jk-mail-eyebrow', 'JAYSONKHAN / MAIL'),
        element('h2', '', t('welcome')), element('p', '', t('signin')));
      login.before(intro);
      var password = document.getElementById('rcmloginpwd');
      if (password) {
        var reveal = element('button', 'jk-password-toggle');
        reveal.type = 'button';
        reveal.setAttribute('aria-controls', password.id);
        function setPasswordVisible(visible) {
          // Change only presentation; never read, copy, log or replace the value.
          password.type = visible ? 'text' : 'password';
          reveal.setAttribute('aria-pressed', String(visible));
          reveal.setAttribute('aria-label', t(visible ? 'hidepassword' : 'showpassword'));
          reveal.title = t(visible ? 'hidepassword' : 'showpassword');
        }
        setPasswordVisible(false);
        reveal.addEventListener('click', function () { setPasswordVisible(password.type === 'password'); });
        password.parentElement.append(reveal);
        window.addEventListener('blur', function () { setPasswordVisible(false); });
        password.closest('form').addEventListener('submit', function () { setPasswordVisible(false); });
      }
    }
    var theme = document.querySelector('#taskmenu a.theme');
    if (theme) {
      function themeLabel() {
        var inner = theme.querySelector('.inner');
        if (inner) inner.textContent = t(theme.classList.contains('light') ? 'lightmode' : 'darkmode');
      }
      themeLabel();
      new MutationObserver(themeLabel).observe(theme, {attributes:true, attributeFilter:['class']});
    }
    var htmlMessage = document.querySelector('#messagebody .message-htmlpart');
    var readerLinks = document.querySelector('#message-header .header-links');
    if (htmlMessage && readerLinks) {
      var readerToggle = element('button', 'jk-reader-toggle', t('originalcolors'));
      readerToggle.type = 'button';
      readerToggle.setAttribute('aria-pressed', 'false');
      readerToggle.addEventListener('click', function () {
        var original = document.body.classList.toggle('jk-mail-original-html');
        readerToggle.setAttribute('aria-pressed', String(original));
        readerToggle.textContent = t(original ? 'adaptcolors' : 'originalcolors');
      });
      readerLinks.append(readerToggle);
    }
    var securityForm = document.getElementById('twofactor_gauthenticator-form');
    if (securityForm) {
      var securityTitle = securityForm.querySelector('h3');
      if (securityTitle) {
        // Upstream QR setup extracts the account after " - " from #prefs-title.
        // Keep that delimiter/account contract; only translate the heading prefix.
        var accountDelimiter = securityTitle.textContent.indexOf(' - ');
        if (accountDelimiter >= 0) securityTitle.textContent = t('twofactortitle') + securityTitle.textContent.slice(accountDelimiter);
      }
      [['2FA_activate', 'activate2fa'], ['2FA_secret', 'secret2fa']].forEach(function (item) {
        var label = securityForm.querySelector('label[for="' + item[0] + '"]');
        if (label) label.textContent = t(item[1]);
      });
      var securityActions = {
        '2FA_change_secret':'showsecret', '2FA_create_secret':'createsecret',
        '2FA_show_recovery_codes':'showrecovery', '2FA_change_qr_code':'showqr',
        '2FA_setup_fields':'setup2fa', '2FA_check_code':'checkcode'
      };
      Object.keys(securityActions).forEach(function (id) {
        var button = document.getElementById(id);
        // These are action labels, never secret/code/password input values.
        if (button && button.type === 'button') button.value = t(securityActions[id]);
      });
      securityForm.querySelectorAll('input[name="2FA_recovery_codes[]"]').forEach(function (input, i) {
        input.setAttribute('aria-label', t('recoverycodes') + ' ' + (i + 1));
        input.autocomplete = 'off';
        if (i === 0 && input.closest('td').previousElementSibling) {
          input.closest('td').previousElementSibling.textContent = t('recoverycodes');
        }
      });
      var codeCheck = document.getElementById('2FA_code_to_check');
      if (codeCheck) codeCheck.setAttribute('aria-label', t('checkcode'));
      securityForm.append(element('p', 'jk-2fa-hint', t('save2fahint')));
    }
    var data = rcmail.env.jaysonkhan_mail_addresses;
    var folders = document.querySelector('#folderlist-content');
    if (!data || !folders || document.querySelector('#jk-mail-aliases')) return;

    var card = element('section', 'jk-mail-card');
    card.append(element('span', 'jk-mail-eyebrow', 'JAYSONKHAN MAIL'),
      element('h2', '', t('oneinbox')), element('p', '', t('aliasesnote')));
    var open = element('button', 'jk-mail-address-button', t('addresses') + ' · ' + data.aliases.length);
    open.type = 'button';
    open.setAttribute('aria-haspopup', 'dialog');
    open.setAttribute('aria-controls', 'jk-mail-aliases');
    card.append(open);
    folders.append(card);

    var dialog = element('dialog', 'jk-mail-dialog');
    dialog.id = 'jk-mail-aliases';
    dialog.setAttribute('aria-labelledby', 'jk-mail-dialog-title');
    var head = element('div', 'jk-mail-dialog-head');
    var title = element('h2', '', t('addresses'));
    title.id = 'jk-mail-dialog-title';
    var close = element('button', 'jk-mail-close', '×');
    close.type = 'button';
    close.setAttribute('aria-label', t('close'));
    head.append(title, close);
    var account = element('div', 'jk-mail-account');
    account.append(element('span', 'jk-mail-eyebrow', t('primary')), element('strong', '', data.mailbox));
    var search = element('input', 'jk-mail-search');
    search.type = 'search';
    search.placeholder = t('search');
    search.setAttribute('aria-label', t('search'));
    var status = element('p', 'jk-mail-status');
    status.setAttribute('role', 'status');
    var list = element('ul', 'jk-mail-alias-list');
    data.aliases.forEach(function (address) {
      var row = element('li', '');
      row.dataset.address = address;
      row.append(element('span', 'jk-mail-alias-address', address));
      var copy = element('button', 'jk-mail-copy', t('copy'));
      copy.type = 'button';
      copy.setAttribute('aria-label', t('copy') + ': ' + address);
      copy.addEventListener('click', async function () {
        try {
          await navigator.clipboard.writeText(address);
          status.textContent = t('copied') + ': ' + address;
        } catch (error) {
          // Keep selectable text and explain the fallback when clipboard is blocked.
          status.textContent = t('copyfallback');
        }
      });
      row.append(copy); list.append(row);
    });
    var empty = element('p', 'jk-mail-empty', t('noresults'));
    empty.hidden = data.aliases.length > 0;
    search.addEventListener('input', function () {
      var query = search.value.trim().toLowerCase();
      var visible = 0;
      Array.from(list.children).forEach(function (row) {
        row.hidden = !row.dataset.address.toLowerCase().includes(query);
        if (!row.hidden) visible++;
      });
      empty.hidden = visible > 0;
    });
    dialog.append(head, account, element('p', 'jk-mail-explainer', t('routing')), search,
      list, empty, status, element('p', 'jk-mail-footnote', t('sending')));
    var attribution = element('a', 'jk-mail-attribution', 'Solar icons · 480 Design · CC BY 4.0');
    attribution.href = 'https://creativecommons.org/licenses/by/4.0/';
    attribution.target = '_blank'; attribution.rel = 'noopener noreferrer';
    dialog.append(attribution); document.body.append(dialog);
    open.addEventListener('click', function () { dialog.showModal(); search.focus(); });
    close.addEventListener('click', function () { dialog.close(); });
    dialog.addEventListener('close', function () { open.focus(); });
    // Keep Roundcube's document-level mail shortcuts outside this modal. In
    // particular Delete must never act on a selected message behind the dialog.
    ['keydown', 'keyup', 'keypress'].forEach(function (type) {
      dialog.addEventListener(type, function (event) {
        event.stopPropagation();
        if (type === 'keydown' && event.key === 'Escape') {
          event.preventDefault(); dialog.close();
        }
      });
    });
    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) {
        var rect = dialog.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
      }
    });
  });
}());
