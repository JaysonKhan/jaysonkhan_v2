<?php
// Included last by the existing config. Credentials, 2FA and identities stay intact.
if (strtolower($_SERVER['HTTP_HOST'] ?? '') === 'mail.jaysonkhan.com') {
    // Loopback connection, but validate the actual IMAP certificate identity.
    $config['imap_conn_options'] = ['ssl' => [
        'verify_peer' => true, 'verify_peer_name' => true,
        'allow_self_signed' => false, 'peer_name' => 'mail.jaysonkhan.com',
    ]];
    $config['product_name'] = 'JaysonKhan Mail';
    // Multiple editable sender profiles; the plugin enforces the own-alias allowlist.
    $config['identities_level'] = 0;
    $config['blankpage_url'] = 'plugins/jaysonkhan_mail/watermark.html?v=20260914-2';
    // Type-specific favicon is a supported Roundcube template API. Use the
    // regenerated transparent owner mark, not a horizontal wordmark in the rail.
    $config['skin_logo'] = [
        '*' => 'plugins/jaysonkhan_mail/assets/icon.png',
        '*[small]' => 'plugins/jaysonkhan_mail/assets/icon.png',
        '*[small-dark]' => 'plugins/jaysonkhan_mail/assets/icon.png',
        '*[dark]' => 'plugins/jaysonkhan_mail/assets/icon.png',
        '*[favicon]' => 'plugins/jaysonkhan_mail/assets/favicon-jayson-v1.png',
    ];
    $config['plugins'] = array_values(array_unique(array_merge($config['plugins'] ?? [], ['jaysonkhan_mail'])));
}
