import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

MAIL = Path(__file__).resolve().parents[1]
ROOT = MAIL.parents[1]
spec = importlib.util.spec_from_file_location('mail_configure', MAIL / 'configure.py')
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class MailSafetyTests(unittest.TestCase):
    def test_exact_aliases_chains_and_multi_recipient(self):
        aliases = 'support@jaysonkhan.com admin@jaysonkhan.com\nhelp@jaysonkhan.com support@jaysonkhan.com\nteam@jaysonkhan.com admin@jaysonkhan.com,second@jaysonkhan.com\n'
        boxes = 'admin@jaysonkhan.com jaysonkhan.com/admin/\nsecond@jaysonkhan.com jaysonkhan.com/second/\n'
        self.assertEqual(config.alias_map(aliases, boxes), {
            'admin@jaysonkhan.com': ['help@jaysonkhan.com', 'support@jaysonkhan.com'],
            'second@jaysonkhan.com': [],
        })

    def test_no_other_domain_catchall_invalid_or_cyclic_aliases(self):
        aliases = '\n'.join([
            '@jaysonkhan.com admin@jaysonkhan.com', 'admin@evil.uz admin@jaysonkhan.com',
            'loop@jaysonkhan.com loop2@jaysonkhan.com', 'loop2@jaysonkhan.com loop@jaysonkhan.com',
            '<script>@jaysonkhan.com admin@jaysonkhan.com', 'bad@jaysonkhan.com missing@jaysonkhan.com',
            'valid@jaysonkhan.com admin@jaysonkhan.com',
            'shared@jaysonkhan.com admin@jaysonkhan.com,person@example.org',
            'partial@jaysonkhan.com admin@jaysonkhan.com,loop@jaysonkhan.com',
        ])
        self.assertEqual(config.alias_map(aliases, 'admin@jaysonkhan.com path/'), {'admin@jaysonkhan.com': ['valid@jaysonkhan.com']})

    def test_config_include_is_idempotent_and_preserves_host_config(self):
        original = "<?php\n$config['plugins']=['twofactor_gauthenticator'];\n?>\n"
        added = config.include_config(original)
        self.assertEqual(config.include_config(added), added)
        self.assertIn("$config['plugins']=['twofactor_gauthenticator'];", added)
        self.assertNotIn('?>', added)
        self.assertEqual(added.count(config.INCLUDE), 1)

    def test_safe_log_is_explicit_in_both_server_blocks(self):
        original = 'server {\n server_name mail.jaysonkhan.com;\n}\nserver {\n server_name mail.jaysonkhan.com;\n}\n'
        added = config.safe_log(original)
        self.assertEqual(added.count('access_log /var/log/nginx/access.log uzexam_safe;'), 2)
        self.assertEqual(config.safe_log(added), added)
        with self.assertRaises(ValueError):
            config.safe_log('server { server_name unexpected; }')

    def test_php_authorization_and_config_contract(self):
        result = subprocess.run(['php', str(MAIL / 'tests/contract.php')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('contracts passed', result.stdout)

    def test_assets_are_local_and_complete(self):
        css = (MAIL / 'jaysonkhan_mail/solar.css').read_text()
        import re
        for asset in re.findall(r'url\((assets/[^)]+)\)', css):
            self.assertTrue((MAIL / 'jaysonkhan_mail' / asset).is_file(), asset)
        for name in ['logo.png', 'icon.png', 'ATTRIBUTION.txt']:
            self.assertTrue((MAIL / 'jaysonkhan_mail/assets' / name).is_file())
        js = (MAIL / 'jaysonkhan_mail/mail.js').read_text()
        self.assertNotIn('innerHTML', js)
        self.assertNotIn('fetch(', js)
        self.assertNotIn('http_post', js)
        self.assertIn('event.stopPropagation()', js)
        self.assertIn("event.key === 'Escape'", js)
        self.assertIn("button.setAttribute('aria-label', label.textContent.trim())", js)
        self.assertIn("if (button.classList.contains('theme')) return", js)
        self.assertIn("document.querySelectorAll('.floating-action-buttons a')", js)
        css = (MAIL / 'jaysonkhan_mail/mail.css').read_text()
        self.assertIn('.header > a.button.icon { width:44px; min-width:44px; flex:0 0 44px; }', css)

    def test_mail_deploy_is_explicit_scoped_and_does_not_auto_stage(self):
        deploy = (ROOT / 'deploy.sh').read_text()
        block = deploy.split('deploy_mail() {', 1)[1].split('\n}\n', 1)[0]
        self.assertIn('git status --porcelain', block)
        self.assertIn('git archive HEAD ops/mail', block)
        self.assertIn('sudo cat /var/lib/jaysonkhan-mail/RELEASE', block)
        self.assertNotIn('git add', block)
        self.assertNotIn('git_push_local', block)
        self.assertNotIn('migrate', block)
        self.assertNotIn('deploy_web', block)
        self.assertIn('== --mail', deploy)
        self.assertLess(deploy.index('== --mail'), deploy.index('git add -A'))

    def test_installer_preserves_mail_and_identity_data(self):
        installer = (MAIL / 'install.sh').read_text()
        self.assertNotIn('/var/mail/vhosts', installer)
        self.assertNotIn('postqueue -f', installer)
        self.assertNotIn('postsuper', installer)
        self.assertIn('sha256sum --check', installer)
        self.assertIn('restore_on_error', installer)
        self.assertIn('2022081200', installer)
        self.assertIn('/run/lock/uzexam-mail-deploy.lock', installer)
        self.assertNotIn('roundcubemail/releases/download', installer)
        self.assertNotIn('systemctl restart jaysonkhan', installer)
        self.assertIn('untouched.sha256', installer)

    def test_presentation_contracts_cover_composer_settings_and_split_buttons(self):
        css = (MAIL / 'jaysonkhan_mail/mail.css').read_text()
        solar = (MAIL / 'jaysonkhan_mail/solar.css').read_text()
        for selector in ['.toolbar a.save', '.toolbar a.attach', '.toolbar a.print',
                         '.formbuttons .submit', '.html-editor > .editor-toolbar > a.mce-i-html',
                         '#sections-table .general .section', '#settings-menu .identities > a',
                         '.menu .dropbutton a.dropdown', '.formbuttons .send']:
            self.assertIn(selector, solar)
        self.assertIn('display:inline-block !important', solar)
        self.assertIn('.header .menu.toolbar a:not(.dropdown)', css)
        self.assertIn('flex-direction:column', css)
        self.assertIn('width:calc(100% - 14px)', css)
        # Geometry must never reveal controls that native responsive CSS hides.
        import re
        for declarations in re.findall(r'\.header > a\.button\.icon\s*\{([^}]+)\}', css):
            self.assertNotRegex(declarations, r'\bdisplay\s*:')
        self.assertIn('position:absolute; top:50%; left:50%; transform:translate(-50%,-50%)', css)
        self.assertIn('html:root .popover .menu li a::before', css)
        self.assertIn('html:root .popover .popover-header a { color:var(--jk-text); }', css)
        self.assertIn('html:root.iframe body.task-settings', css)
        self.assertIn('html:root.layout-phone #messagelist td.flags', css)
        # Owner-authorized dark reading palette has an original-colors opt-out.
        self.assertIn('html.dark-mode body:not(.jk-mail-original-html)', css)
        self.assertNotIn('filter:invert', css)
        self.assertIn('#messagebody .message-part div.pre', css)

    def test_reported_populated_and_localized_ui_regressions(self):
        css = (MAIL / 'jaysonkhan_mail/mail.css').read_text()
        js = (MAIL / 'jaysonkhan_mail/mail.js').read_text()
        self.assertIn('> .googie_edit_layer { padding-top:56px; }', css)
        self.assertIn('> .editor-toolbar { height:40px;', css)
        self.assertIn('white-space:normal; overflow:visible; text-overflow:clip', css)
        self.assertIn('#taskmenu .special-buttons { width:100%;', css)
        self.assertIn('#layout-menu { position:relative; width:96px; min-width:96px; }', css)
        self.assertIn('#twofactor_gauthenticator-form input[type=password]', css)
        self.assertIn('td:not(.title):has(input) { display:flex;', css)
        self.assertIn('-webkit-text-fill-color:var(--jk-text) !important', css)
        self.assertIn('1000px var(--jk-bg) inset !important', css)
        self.assertIn("password.type = visible ? 'text' : 'password'", js)
        self.assertNotIn('password.value', js)
        self.assertIn("window.addEventListener('blur'", js)
        self.assertIn("securityTitle.textContent.slice(accountDelimiter)", js)
        self.assertIn("body.classList.toggle('jk-mail-original-html')", js)
        self.assertIn("require __DIR__ . '/uz_UZ.inc'", (MAIL / 'jaysonkhan_mail/localization/uz.inc').read_text())
        for locale in ['en_US', 'uz_UZ', 'ru_RU']:
            labels = (MAIL / f'jaysonkhan_mail/localization/{locale}.inc').read_text()
            for key in ['showpassword', 'hidepassword', 'originalcolors', 'adaptcolors', 'save2fahint']:
                self.assertIn(f"'{key}' =>", labels)

    def test_favicon_and_transparent_illustrations_are_local(self):
        import struct
        config_text = (MAIL / 'config.inc.php').read_text()
        self.assertIn("'*[favicon]'", config_text)
        for path in [MAIL / 'artwork/mail-empty-v1.png', MAIL / 'artwork/contacts-empty-v1.png',
                     MAIL / 'jaysonkhan_mail/assets/icon.png']:
            content = path.read_bytes()
            self.assertEqual(content[:8], b'\x89PNG\r\n\x1a\n')
            width, height, depth, color = struct.unpack('>IIBB', content[16:26])
            self.assertEqual(color, 6, 'RGBA required for both themes')
            self.assertGreater(width, 0)
            self.assertGreater(height, 0)
        for name in ['mail-empty-v1.webp', 'contacts-empty-v1.webp']:
            content = (MAIL / 'jaysonkhan_mail/assets' / name).read_bytes()
            self.assertEqual(content[:4], b'RIFF')
            self.assertEqual(content[8:12], b'WEBP')
            self.assertLess(len(content), 150_000, 'keep mobile decoration lightweight')
        watermark = (MAIL / 'jaysonkhan_mail/watermark.html').read_text()
        self.assertIn("task-addressbook", watermark)
        self.assertIn("task-settings", watermark)
        self.assertNotIn('innerHTML', watermark)
        self.assertNotIn('parent.rcmail', watermark)


if __name__ == '__main__':
    unittest.main()
