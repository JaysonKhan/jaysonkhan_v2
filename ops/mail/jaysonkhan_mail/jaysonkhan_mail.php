<?php
/** JaysonKhan presentation and verified sender-alias policy. Mail content is never rewritten. */
class jaysonkhan_mail extends rcube_plugin
{
    protected $allowed_senders = [];
    public function init()
    {
        // The installation also serves mail.uzexam.uz. Do not rebrand it.
        if (strtolower($_SERVER['HTTP_HOST'] ?? '') !== 'mail.jaysonkhan.com') {
            return;
        }
        $rc = rcmail::get_instance();
        $this->include_stylesheet('mail.css');
        $this->include_stylesheet('solar.css');
        $this->include_script('mail.js');
        $this->add_texts('localization/', true);
        $rc->output->set_env('jaysonkhan_mail_brand', true);

        // Alias routing is exported from Postfix into a non-public, root-owned file.
        // Never expose other mailboxes' mappings, including before login/2FA.
        if (!$rc->user || !$rc->user->ID || !empty($_SESSION['temp'])) {
            return;
        }
        $prefs = $rc->user->get_prefs();
        if (!empty($prefs['twofactor_gauthenticator']['activate'])
            && (empty($_SESSION['twofactor_gauthenticator_2FA_login'])
                || $_SESSION['twofactor_gauthenticator_2FA_login'] < ($_SESSION['twofactor_gauthenticator_login'] ?? PHP_INT_MAX))) {
            return;
        }
        $username = strtolower($rc->user->get_username());
        if (!filter_var($username, FILTER_VALIDATE_EMAIL) || !str_ends_with($username, '@jaysonkhan.com')) {
            return;
        }
        $this->add_hook('identity_form', [$this, 'identity_form']);
        $this->add_hook('identity_create', [$this, 'identity_save']);
        $this->add_hook('identity_update', [$this, 'identity_save']);
        $this->add_hook('identity_select', [$this, 'identity_select']);
        $this->add_hook('message_before_send', [$this, 'before_send']);
        // Same username on a different IMAP backend is not the same owner.
        // Keep the deny hooks registered, but grant nothing on backend mismatch.
        if (($rc->user->data['mail_host'] ?? '') !== '127.0.0.1') {
            return;
        }
        $aliases = self::aliases_for($username, '/var/lib/jaysonkhan-mail/aliases.json');
        // A missing/corrupt export must never grant aliases. The primary mailbox
        // remains usable. These hooks run only after the complete login/2FA gate.
        $this->allowed_senders = array_values(array_unique(array_merge([$username], $aliases ?? [])));
        if ($aliases !== null) {
            $rc->output->set_env('jaysonkhan_mail_addresses', [
                'mailbox' => $username,
                'aliases' => $aliases,
            ]);
        }
    }

    public function identity_select($args)
    {
        // Historical profiles can reference another real mailbox. Preserve
        // stored names/signatures/default flags, but never preselect an unowned
        // sender for a new message or reply. Explicit draft/POST is still guarded
        // by before_send (including both visible From and SMTP envelope).
        $selected = $args['selected'] ?? 0;
        $email = strtolower($args['identities'][$selected]['email'] ?? '');
        if (!in_array($email, $this->allowed_senders, true)) {
            foreach ($args['identities'] as $index => $identity) {
                if (in_array(strtolower($identity['email']), $this->allowed_senders, true)) {
                    $args['selected'] = $index;
                    break;
                }
            }
        }
        return $args;
    }

    public function identity_form($args)
    {
        if (isset($args['form']['addressing']['content']['email'])) {
            $args['form']['addressing']['content']['email'] = [
                'type' => 'select', 'skip-empty' => true,
                'options' => array_combine($this->allowed_senders, $this->allowed_senders),
            ];
        }
        return $args;
    }

    public function identity_save($args)
    {
        $email = strtolower(trim($args['record']['email'] ?? ''));
        if (!in_array($email, $this->allowed_senders, true)) {
            $args['abort'] = true;
            $args['result'] = false;
            $args['message'] = 'jaysonkhan_mail.sendernotallowed';
        } else {
            $args['record']['email'] = $email;
        }
        return $args;
    }

    public function before_send($args)
    {
        // Enforce both SMTP envelope and visible From; checking the dropdown
        // alone would allow a forged HTTP request or an obsolete stored profile.
        $headers = $args['message']->headers();
        $from_headers = [];
        foreach ($headers as $name => $value) {
            if (strtolower($name) === 'from') $from_headers[] = $value;
        }
        $senders = count($from_headers) === 1
            ? rcube_mime::decode_address_list($from_headers[0], null, false) : [];
        $allowed = in_array(strtolower($args['from'] ?? ''), $this->allowed_senders, true)
            && count($senders) === 1
            && in_array(strtolower(reset($senders)['mailto'] ?? ''), $this->allowed_senders, true);
        if (!$allowed) {
            $args['abort'] = true;
            $args['result'] = false;
            $args['error'] = ['label' => 'jaysonkhan_mail.sendernotallowed', 'vars' => []];
        }
        return $args;
    }

    public static function aliases_for($username, $path)
    {
        if (!filter_var($username, FILTER_VALIDATE_EMAIL) || !str_ends_with($username, '@jaysonkhan.com')) {
            return null;
        }
        if (!is_readable($path)) {
            return null; // No fabricated/stale list when the authoritative export is unavailable.
        }
        $map = json_decode(file_get_contents($path), true);
        if (!is_array($map) || !isset($map[$username]) || !is_array($map[$username])) {
            return null;
        }
        $aliases = array_filter($map[$username], function ($value) use ($username) {
            return is_string($value) && $value !== $username
                && filter_var($value, FILTER_VALIDATE_EMAIL)
                && str_ends_with(strtolower($value), '@jaysonkhan.com');
        });
        $aliases = array_map('strtolower', $aliases);
        sort($aliases, SORT_STRING);
        return array_values(array_unique($aliases));
    }
}
