# myeffort

## Passport upload agent

This repository contains a Python agent that:

1. Opens a simple browser UI for uploading a passport file directly.
2. Extracts the passport holder name, passport number, and expiry date from the uploaded file.
3. Shows the extracted details in the browser.

The extractor supports:

- Text files containing labelled fields such as `Name`, `Passport Number`, and `Date of Expiry`.
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

### Run

```bash
passport-email-agent run
```

Then open:

```text
http://127.0.0.1:8000
```

Upload a passport PDF, image, or text file from the page. The server processes the
file in memory and displays the extracted details.

To listen on another host or port:

```bash
passport-email-agent run --host 0.0.0.0 --port 8080
```

You can also test extraction locally without opening the UI:

```bash
passport-email-agent extract ./passport.txt
```

### Optional email workflow

The older email workflow is still available as an explicit command:

```bash
passport-email-agent email --recipient muzammil.younus@al-ghurair.com
```

Set these environment variables before using the email workflow:

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
```

### Security notes

Passport documents contain personal data. Run the UI only on trusted networks, avoid
logging raw files or extracted details, and delete passport files after processing
unless retention is explicitly required.
