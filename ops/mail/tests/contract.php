<?php
error_reporting(E_ALL);
set_error_handler(function ($severity, $message) { throw new Exception($message); });
class rcube_plugin {
    public $hooks = [];
    public function add_hook($name, $handler) { $this->hooks[$name] = $handler; }
    public function include_stylesheet($x) {}
    public function include_script($x) {}
    public function add_texts($x, $y) {}
}
class Output {
    public $env = [];
    public function set_env($key, $value) { $this->env[$key] = $value; }
}
class User {
    public $ID = 1;
    public $prefs = [];
    public $data = ['mail_host' => '127.0.0.1'];
    public function get_prefs() { return $this->prefs; }
    public function get_username() { return 'admin@jaysonkhan.com'; }
}
class rcmail {
    public static $instance;
    public static function get_instance() { return self::$instance; }
}
function check($value, $label) {
    if (!$value) { throw new Exception($label); }
}
require __DIR__ . '/../jaysonkhan_mail/jaysonkhan_mail.php';
class SenderTestPlugin extends jaysonkhan_mail {
    public function allow($values) { $this->allowed_senders = $values; }
}
// Decoder is an upstream contract; supply its structured output to test the
// policy independently, including multiple visible From addresses.
class rcube_mime {
    public static $decoded = [];
    public static function decode_address_list($value, $max, $check) { return self::$decoded; }
}
class SenderTestMessage {
    public function headers() { return ['From' => 'JaysonKhan Support <support@jaysonkhan.com>']; }
}
$sender = new SenderTestPlugin();
$sender->allow(['admin@jaysonkhan.com', 'support@jaysonkhan.com']);
$choice = $sender->identity_select(['selected'=>null, 'identities'=>[
    ['email'=>'private@jaysonkhan.com'], ['email'=>'support@jaysonkhan.com']]]);
check($choice['selected'] === 1, 'unowned default never preselected');
$choice = $sender->identity_select(['selected'=>1, 'identities'=>[
    ['email'=>'admin@jaysonkhan.com'], ['email'=>'support@jaysonkhan.com']]]);
check($choice['selected'] === 1, 'valid reply sender preserved');
$args = ['record' => ['email' => 'SUPPORT@jaysonkhan.com', 'signature' => 'keep']];
$saved = $sender->identity_save($args);
check($saved['record']['email'] === 'support@jaysonkhan.com' && $saved['record']['signature'] === 'keep', 'verified alias profile editable');
foreach (['evil@example.org', 'private@jaysonkhan.com', 'support@jaysonkhan.com.evil.org', ''] as $invalid) {
    check($sender->identity_save(['record' => ['email' => $invalid]])['abort'], 'unowned sender profile rejected');
}
$form = $sender->identity_form(['form' => ['addressing' => ['content' => ['email' => ['type' => 'text']]]]]);
check(array_keys($form['form']['addressing']['content']['email']['options']) === ['admin@jaysonkhan.com', 'support@jaysonkhan.com'], 'only own email options');
$send = ['message' => new SenderTestMessage(), 'from' => 'support@jaysonkhan.com'];
rcube_mime::$decoded = [['mailto' => 'support@jaysonkhan.com']];
check(empty($sender->before_send($send)['abort']), 'alias envelope and From accepted');
$bad = $send; $bad['from'] = 'private@jaysonkhan.com';
check($sender->before_send($bad)['abort'], 'forged envelope rejected');
rcube_mime::$decoded = [['mailto' => 'private@jaysonkhan.com']];
check($sender->before_send($send)['abort'], 'forged visible From rejected');
rcube_mime::$decoded = [['mailto' => 'support@jaysonkhan.com'], ['mailto' => 'admin@jaysonkhan.com']];
check($sender->before_send($send)['abort'], 'multiple From senders rejected');
$sender->allow(['admin@jaysonkhan.com']);
rcube_mime::$decoded = [['mailto' => 'support@jaysonkhan.com']];
check($sender->before_send($send)['abort'], 'revoked alias rejected before SMTP');
$fixture = tempnam(sys_get_temp_dir(), 'jk-mail-test-');
try {
    file_put_contents($fixture, json_encode([
        'admin@jaysonkhan.com' => ['support@jaysonkhan.com', 'support@jaysonkhan.com', '<script>@jaysonkhan.com', 'foreign@example.org'],
        'other@jaysonkhan.com' => ['private@jaysonkhan.com'],
    ]));
    check(jaysonkhan_mail::aliases_for('admin@jaysonkhan.com', $fixture) === ['support@jaysonkhan.com'], 'only valid own aliases');
    check(jaysonkhan_mail::aliases_for('missing@jaysonkhan.com', $fixture) === null, 'unknown account');
    check(jaysonkhan_mail::aliases_for('admin@elsewhere.uz', $fixture) === null, 'tenant boundary');
    check(jaysonkhan_mail::aliases_for('admin@jaysonkhan.com', $fixture . '-absent') === null, 'missing map');
    file_put_contents($fixture, 'not json');
    check(jaysonkhan_mail::aliases_for('admin@jaysonkhan.com', $fixture) === null, 'corrupt map');
} finally { unlink($fixture); }

$rc = new stdClass(); $rc->output = new Output(); $rc->user = new User();
rcmail::$instance = $rc;
$plugin = new jaysonkhan_mail();
$_SERVER['HTTP_HOST'] = 'mail.uzexam.uz'; $_SESSION = [];
$plugin->init(); check($rc->output->env === [], 'other host unchanged');
$_SERVER['HTTP_HOST'] = 'mail.jaysonkhan.com';
$rc->user->ID = 0; $plugin->init();
check(!isset($rc->output->env['jaysonkhan_mail_addresses']), 'unauthenticated must not receive aliases');
$rc->user->ID = 1; $_SESSION['temp'] = true; $plugin->init();
check(!isset($rc->output->env['jaysonkhan_mail_addresses']), 'temporary session');
$_SESSION = ['twofactor_gauthenticator_login' => 100];
$rc->user->prefs = ['twofactor_gauthenticator' => ['activate' => true]];
$plugin->init(); check(!isset($rc->output->env['jaysonkhan_mail_addresses']), '2FA pending');
$_SESSION['twofactor_gauthenticator_2FA_login'] = 99;
$plugin->init(); check(!isset($rc->output->env['jaysonkhan_mail_addresses']), 'stale 2FA');
check($plugin->hooks === [], 'no sender/profile hooks before complete authentication');
$_SESSION = []; $rc->user->prefs = []; $rc->user->data['mail_host'] = 'another.backend';
$blocked = new jaysonkhan_mail(); $blocked->init();
check(isset($blocked->hooks['message_before_send']), 'foreign backend is explicitly denied');
check($blocked->identity_save(['record'=>['email'=>'admin@jaysonkhan.com']])['abort'], 'same username on foreign backend cannot claim aliases');

$config = ['plugins' => ['archive', 'twofactor_gauthenticator'], 'sentinel' => 'preserved'];
include __DIR__ . '/../config.inc.php';
include __DIR__ . '/../config.inc.php';
check($config['plugins'] === ['archive', 'twofactor_gauthenticator', 'jaysonkhan_mail'], 'plugins preserved/idempotent');
check($config['sentinel'] === 'preserved', 'config preserved');
check($config['imap_conn_options']['ssl']['verify_peer'] === true, 'IMAP validation');
check($config['identities_level'] === 0, 'multiple editable sender profiles');
check($config['skin_logo']['*[favicon]'] === 'plugins/jaysonkhan_mail/assets/favicon-jayson-v1.png', 'branded favicon');
check($config['skin_logo']['*'] === $config['skin_logo']['*[dark]'], 'transparent mark in both themes');
$_SERVER['HTTP_HOST'] = 'mail.uzexam.uz';
$config = ['sentinel' => 'original'];
include __DIR__ . '/../config.inc.php';
check($config === ['sentinel' => 'original'], 'other host config unchanged');
echo "Mail PHP contracts passed\n";
