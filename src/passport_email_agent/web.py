from __future__ import annotations

import cgi
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from passport_email_agent.extractor import PassportExtractionError, PassportExtractor
from passport_email_agent.models import PassportData


class PassportUploadServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        extractor: PassportExtractor | None = None,
    ) -> None:
        super().__init__(server_address, PassportUploadHandler)
        self.extractor = extractor or PassportExtractor()


class PassportUploadHandler(BaseHTTPRequestHandler):
    server: PassportUploadServer

    def do_GET(self) -> None:
        self._send_html(HTTPStatus.OK, self._render_form())

    def do_POST(self) -> None:
        if self.path != "/upload":
            self._send_html(HTTPStatus.NOT_FOUND, self._render_error("Page not found."))
            return

        try:
            filename, content_type, payload = self._read_upload()
            data = self.server.extractor.extract(
                payload=payload,
                filename=filename,
                content_type=content_type,
            )
        except (PassportExtractionError, ValueError) as exc:
            self._send_html(HTTPStatus.BAD_REQUEST, self._render_error(str(exc)))
            return

        self._send_html(HTTPStatus.OK, self._render_result(data))

    def log_message(self, format: str, *args: object) -> None:
        # Avoid logging uploaded file names or extracted passport data.
        print(f"{self.address_string()} - {format % args}")

    def _read_upload(self) -> tuple[str, str, bytes]:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("multipart/form-data"):
            raise PassportExtractionError("Upload must use multipart/form-data.")

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            raise PassportExtractionError("Upload is missing content length.")

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": content_length,
            },
        )
        file_item = form["passport_file"] if "passport_file" in form else None

        if file_item is None or not getattr(file_item, "filename", ""):
            raise PassportExtractionError("Please select a passport file to upload.")

        payload = file_item.file.read()
        if not payload:
            raise PassportExtractionError("Uploaded passport file is empty.")

        return (
            str(file_item.filename),
            str(getattr(file_item, "type", "") or ""),
            payload,
        )

    def _send_html(self, status: HTTPStatus, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _render_form(self) -> str:
        return _page(
            "Upload passport",
            """
            <section class="card">
              <h1>Upload passport file</h1>
              <p>Select a passport PDF, image, or text file. The file is processed in memory and is not stored by this server.</p>
              <form action="/upload" method="post" enctype="multipart/form-data">
                <label for="passport_file">Passport file</label>
                <input id="passport_file" name="passport_file" type="file" accept=".pdf,.txt,.jpg,.jpeg,.png,.tiff,.webp,image/*,application/pdf,text/plain" required>
                <button type="submit">Extract passport details</button>
              </form>
            </section>
            """,
        )

    def _render_result(self, data: PassportData) -> str:
        return _page(
            "Passport details",
            f"""
            <section class="card">
              <h1>Passport details</h1>
              <dl>
                <dt>Name</dt>
                <dd>{escape(data.full_name)}</dd>
                <dt>Passport Number</dt>
                <dd>{escape(data.passport_number)}</dd>
                <dt>Expiry Date</dt>
                <dd>{escape(data.expiry_date.isoformat())}</dd>
              </dl>
              <p class="hint">Please verify these details before using them.</p>
              <a class="button secondary" href="/">Upload another file</a>
            </section>
            """,
        )

    def _render_error(self, message: str) -> str:
        return _page(
            "Extraction failed",
            f"""
            <section class="card error">
              <h1>Could not extract passport details</h1>
              <p>{escape(message)}</p>
              <a class="button secondary" href="/">Try another file</a>
            </section>
            """,
        )


def run_upload_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    extractor: PassportExtractor | None = None,
    notify: Callable[[str], None] = print,
) -> None:
    server = PassportUploadServer((host, port), extractor=extractor)
    url = f"http://{host}:{server.server_port}"
    notify(f"Passport upload agent running at {url}")
    notify("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        notify("\nStopping passport upload agent.")
    finally:
        server.server_close()


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: Arial, sans-serif;
      line-height: 1.5;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f4f6f8;
      color: #17202a;
    }}
    .card {{
      width: min(92vw, 560px);
      padding: 32px;
      border-radius: 16px;
      background: white;
      box-shadow: 0 20px 60px rgba(23, 32, 42, 0.12);
    }}
    h1 {{
      margin-top: 0;
    }}
    label {{
      display: block;
      margin: 24px 0 8px;
      font-weight: 700;
    }}
    input {{
      box-sizing: border-box;
      width: 100%;
      padding: 12px;
      border: 1px solid #cfd8dc;
      border-radius: 8px;
      background: white;
    }}
    button, .button {{
      display: inline-block;
      margin-top: 24px;
      padding: 12px 18px;
      border: 0;
      border-radius: 8px;
      background: #1455d9;
      color: white;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
    }}
    .secondary {{
      background: #5d6d7e;
    }}
    dl {{
      display: grid;
      grid-template-columns: max-content 1fr;
      gap: 12px 20px;
    }}
    dt {{
      font-weight: 700;
    }}
    dd {{
      margin: 0;
    }}
    .hint {{
      color: #5d6d7e;
    }}
    .error {{
      border-top: 6px solid #c0392b;
    }}
    @media (prefers-color-scheme: dark) {{
      body {{
        background: #101820;
        color: #ecf0f1;
      }}
      .card {{
        background: #17202a;
      }}
      input {{
        background: #101820;
        color: #ecf0f1;
      }}
    }}
  </style>
</head>
<body>
{body}
</body>
</html>"""
