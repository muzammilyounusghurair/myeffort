# myeffort

## Passport email agent

This repository contains a Python agent that:

1. Emails `muzammil.younus@al-ghurair.com` asking for a passport file.
2. Polls an IMAP inbox for a reply with the request reference in the subject/body.
3. Extracts the passport holder name, passport number, and expiry date from the attached file.
4. Emails the extracted details back to the same recipient.

The extractor supports:

- Text attachments containing labelled fields such as `Name`, `Passport Number`, and `Date of Expiry`.
- Passport MRZ text.
- PDFs with embedded text via `pypdf`.
- Image OCR when installed with the optional `ocr` extras and a working Tesseract binary.

### Install

```bash
python -m pip install -e ".[dev]"
```

For image OCR support:

```bash
python -m pip install -e ".[ocr]"
```

### Configure email

Set these environment variables for the mailbox the agent should use:

```bash
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USERNAME="agent@example.com"
export SMTP_PASSWORD="password"
export SMTP_FROM="agent@example.com"

export IMAP_HOST="imap.example.com"
export IMAP_PORT="993"
export IMAP_USERNAME="agent@example.com"
export IMAP_PASSWORD="password"
export PASSPORT_AGENT_RECIPIENT="muzammil.younus@al-ghurair.com"
```

Optional settings:

- `SMTP_STARTTLS` defaults to `true`.
- `IMAP_SSL` defaults to `true`.
- `IMAP_MAILBOX` defaults to `INBOX`.
- `POLL_INTERVAL_SECONDS` defaults to `30`.
- `REPLY_TIMEOUT_SECONDS` defaults to `1800`.

### Run

```bash
passport-email-agent run
```

Or override the recipient:

```bash
passport-email-agent run --recipient muzammil.younus@al-ghurair.com
```

You can test extraction locally without sending email:

```bash
passport-email-agent extract ./passport.txt
```

### Security notes

Passport documents contain personal data. Use a locked-down mailbox, avoid logging raw
attachments, and delete passport files after processing unless retention is explicitly required.
