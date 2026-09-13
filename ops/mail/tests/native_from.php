<?php
// Integration against the pinned vendor MIME decoder. No mail transport call.
error_reporting(E_ALL);
$vendor = $argv[1] ?? '';
require $vendor . '/program/lib/Roundcube/rcube_utils.php';
require $vendor . '/program/lib/Roundcube/rcube_mime.php';
class rcube_plugin {}
require __DIR__ . '/../jaysonkhan_mail/jaysonkhan_mail.php';
class PolicyProbe extends jaysonkhan_mail {
    public function allow($values) { $this->allowed_senders = $values; }
}
class MIMEProbe {
    public $from;
    public function headers() { return ['From' => $this->from]; }
}
$policy = new PolicyProbe();
$policy->allow(['admin@jaysonkhan.com', 'support@jaysonkhan.com']);
$cases = [
    ['support@jaysonkhan.com', true],
    ['"Khan, Support" <support@jaysonkhan.com>', true],
    ['=?UTF-8?Q?Yordam?= <support@jaysonkhan.com>', true],
    ['support@jaysonkhan.com, admin@jaysonkhan.com', false],
    ['"support@jaysonkhan.com" <other@jaysonkhan.com>', false],
    ['support@jaysonkhan.com.evil.org', false],
    ['', false],
];
foreach ($cases as [$from, $allowed]) {
    $message = new MIMEProbe(); $message->from = $from;
    $result = $policy->before_send(['message'=>$message,'from'=>'support@jaysonkhan.com']);
    if (empty($result['abort']) !== $allowed) { throw new Exception('Native MIME contract failed'); }
}
echo "Native MIME sender contracts passed\n";
