import re

SENSITIVE_PATTERNS = {
    "OPENAI_API_KEY": re.compile(r'sk-(?:proj-)?[a-zA-Z0-9_\-]{40,}'),
    "GOOGLE_GEMINI_API_KEY": re.compile(r'AIza[0-9A-Za-z\-_]{35}'),
    "AWS_ACCESS_KEY_ID": re.compile(r'(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}'),
    "AWS_SECRET_ACCESS_KEY": re.compile(r'(?:aws_secret|aws_access)[\w\s]*[=:] *([a-zA-Z0-9/+=]{40})', flags=re.IGNORECASE),
    "GITHUB_TOKEN": re.compile(r'(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,255}'),
    "GITLAB_TOKEN": re.compile(r'glpat-[a-zA-Z0-9\-]{20}'),
    "SLACK_TOKEN": re.compile(r'xox[baprs]-[a-zA-Z0-9]{10,}-[a-zA-Z0-9]{10,}(?:-[a-zA-Z0-9]{10,})?-[a-zA-Z0-9]{24,32}'),
    "DISCORD_WEBHOOK": re.compile(r'https://discord(?:app)?\.com/api/webhooks/[0-9]{17,19}/([a-zA-Z0-9\-_]{68})', flags=re.IGNORECASE),
    "DISCORD_BOT_TOKEN": re.compile(r'[MNO][a-zA-Z0-9_-]{23,25}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}'),
    "TELEGRAM_BOT_TOKEN": re.compile(r'[0-9]{8,10}:[a-zA-Z0-9_-]{35}'),
    "STRIPE_SECRET_KEY": re.compile(r'sk_(?:live|test)_[0-9a-zA-Z]{24}'),
    "SENDGRID_API_KEY": re.compile(r'SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}'),
    "TWILIO_ACCOUNT_SID": re.compile(r'AC[a-zA-Z0-9]{32}'),
    "TWILIO_AUTH_TOKEN": re.compile(r'(?:twilio)[\w\s]*[=:] *([a-z0-9]{32})', flags=re.IGNORECASE),
    "FIREBASE_SERVER_KEY": re.compile(r'AAAA[a-zA-Z0-9_-]{38}:[a-zA-Z0-9_-]{140}'),

    # ==================== 2. AUTHENTICATION & SECRETS ====================
    "PRIVATE_KEY": re.compile(r'-----BEGIN.*?PRIVATE KEY.*?-----END.*?PRIVATE KEY-----', flags=re.IGNORECASE | re.DOTALL),
    "JWT_TOKEN": re.compile(r'ey[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}'),
    "BEARER_TOKEN": re.compile(r'(?:bearer|token)[ \t]+([a-zA-Z0-9_\-\.]{20,})', flags=re.IGNORECASE),
    "BASIC_AUTH_HEADER": re.compile(r'basic[ \t]+([a-zA-Z0-9\+/=]{20,})', flags=re.IGNORECASE),
    "COOKIE_SESSION": re.compile(r'(?:session|connect\.sid|PHPSESSID|JSESSIONID)[\s]*[=:] *([a-zA-Z0-9_\-]{16,})', flags=re.IGNORECASE),
    "OAUTH_REFRESH_TOKEN": re.compile(r'1//[a-zA-Z0-9_\-]{40,}'),
    "GENERIC_SECRET_VALUE": re.compile(r'(?:api_key|apikey|token|secret|auth)[\s]*[=:]? *[\'"]([^\'"]{10,})[\'"]', flags=re.IGNORECASE),
    "PASSWORD_VALUE": re.compile(r'(?:password|passwd|pass|pwd|sandi)[\d]*[\s]*[=:] *([^\s;,\.]+)', flags=re.IGNORECASE),
    "USERNAME_VALUE": re.compile(r'(?:username|user|usr)[\d]*[\s]*[=:] *([^\s;,\.]+)', flags=re.IGNORECASE),
    "HIGH_ENTROPY_SECRET": re.compile(r'(?<=[=\s:\'"])[a-zA-Z0-9\+/]{40,}(?=[=\s:\'"\n;]|$)'),

    # ==================== 3. URLS & DATABASE CONNECTIONS ====================
    "DATABASE_URL_CREDENTIALS": re.compile(r'(?:mysql|postgres|postgresql|mongodb|redis|sqlite)://[a-zA-Z0-9_\-]+:([^@\s]+)@[a-zA-Z0-9_\-\.]+:\d+/[a-zA-Z0-9_\-]+', flags=re.IGNORECASE),
    "CLOUDINARY_CREDENTIALS": re.compile(r'cloudinary://[0-9]+:([a-zA-Z0-9_\-]+)@[a-zA-Z0-9_\-]+', flags=re.IGNORECASE),
    "URL_WITH_CREDENTIALS": re.compile(r'https?://[a-zA-Z0-9_\-]+:([^@\s]+)@[a-zA-Z0-9_\-\.]+', flags=re.IGNORECASE),
    "GIT_URL_CREDENTIALS": re.compile(r'(?:git|https?)://[a-zA-Z0-9_\-]+:([^@\s]+)@(?:github\.com|gitlab\.com|bitbucket\.org)', flags=re.IGNORECASE),

    # ==================== 4. PII (PERSONAL IDENTIFIABLE INFO) ====================
    "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "INDONESIAN_PHONE": re.compile(r'\b(?:\+62|62|0)[2-9]\d{7,11}\b'),
    "INTERNATIONAL_PHONE_CTX": re.compile(r'(?:phone|telepon|hp|no_hp)[\s]*[=:] *(\+?[0-9 \t\-]{8,15})', flags=re.IGNORECASE),
    "PASSPORT_CTX": re.compile(r'(?:passport|paspor)[\s]*[=:] *([A-Za-z0-9]{7,9})', flags=re.IGNORECASE),
    "DATE_OF_BIRTH_CTX": re.compile(r'(?:dob|date_of_birth|tanggal_lahir|tgl_lahir|lahir)[\s]*[=:] *([\d]{2,4}[-/][\d]{2}[-/][\d]{2,4})', flags=re.IGNORECASE),
    
    # KUNCI BARIS BARU: Menggunakan spasi manual keras, bukan \s
    "FULL_NAME_CTX": re.compile(r'(?:full_name|nama_lengkap|nama)[\s]*[=:] *([A-Z][a-z]+(?: [A-Z][a-z]+)*)', flags=re.IGNORECASE),
    # ADDRESS_CTX Anti-Greedy: Berhenti mendeteksi secara cerdas jika di depannya mendeteksi koma/spasi yang mengarah ke kata kunci sensitif lain
    "ADDRESS_CTX": re.compile(r'(?:address|alamat|domisili)[\s\w]*[=:] *([^,\n;:=]{5,})', flags=re.IGNORECASE),
    
    # INDONESIAN PII
    "NIK_KTP_CTX": re.compile(r'(?:nik|ktp|id_card)[\s]*[=:] *(\d{16})', flags=re.IGNORECASE),
    "NIK_KTP_DIRECT": re.compile(r'\b\d{16}\b'),
    "KARTU_KELUARGA_CTX": re.compile(r'(?:kk|kartu_keluarga|no_kk)[\s]*[=:] *(\d{16})', flags=re.IGNORECASE),
    "NPWP_CTX": re.compile(r'(?:npwp)[\s]*[=:] *([\d\.\-]{15,20})', flags=re.IGNORECASE),
    "BPJS_CTX": re.compile(r'(?:bpjs|kes|ketenagakerjaan)[\s]*[=:] *(\d{13})', flags=re.IGNORECASE),
    "BANK_ACCOUNT_CTX": re.compile(r'(?:rekening|account_number|norek|bank)[\s]*[=:] *(\d{10,16})', flags=re.IGNORECASE),
    "CREDIT_CARD": re.compile(r'\b(?:\d[ \t\-]*?){13,16}\b'),

    # ==================== 5. INTERNAL INFRASTRUCTURE & MARKERS ====================
    "INTERNAL_HOSTNAME": re.compile(r'\b[a-zA-Z0-9_\-]+\.(?:local|internal|corp|lan)\b', flags=re.IGNORECASE),
    "IPV4_GENERAL": re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
    "LOCALHOST_URL": re.compile(r'https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/[^\s;]*)?', flags=re.IGNORECASE),
    "MAC_ADDRESS": re.compile(r'\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b'),
    "KUBECONFIG_SECRET": re.compile(r'(?:client-certificate-data|client-key-data): *([a-zA-Z0-9\+/=]{40,})', flags=re.IGNORECASE),
    
    "CONFIDENTIAL_MARKER": re.compile(r'\b(?:confidential|rahasia|internal_use_only|strictly_private)\b', flags=re.IGNORECASE),
    "SQL_DUMP_MARKER": re.compile(r'INSERT INTO[ \t]+.*?[ \t]+VALUES *\(', flags=re.IGNORECASE),
    "ENV_FILE_MARKER": re.compile(r'^(?:NODE_ENV|APP_ENV|DB_CONNECTION)=', flags=re.IGNORECASE | re.MULTILINE),
}

RISK_WEIGHTS = {
    "OPENAI_API_KEY": 50, "AWS_SECRET_ACCESS_KEY": 50, "PRIVATE_KEY": 50,
    "DATABASE_URL_CREDENTIALS": 40, "PASSWORD_VALUE": 40, "JWT_TOKEN": 30,
    "NIK_KTP_DIRECT": 30, "IPV4_GENERAL": 20, 
    "EMAIL": 10, "INDONESIAN_PHONE": 10, "FULL_NAME_CTX": 5, "ADDRESS_CTX": 5
}