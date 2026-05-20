from __future__ import annotations

import http.client
import threading

from passport_email_agent.web import PassportUploadServer


def test_upload_ui_extracts_passport_details_from_file() -> None:
    server = PassportUploadServer(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        boundary = "----passport-test-boundary"
        file_payload = (
            b"Name: Muzammil Younus\n"
            b"Passport Number: A1234567\n"
            b"Date of Expiry: 20 May 2031\n"
        )
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="passport_file"; filename="passport.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
        ).encode("utf-8") + file_payload + f"\r\n--{boundary}--\r\n".encode("utf-8")

        connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
        connection.request(
            "POST",
            "/upload",
            body=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
        )
        response = connection.getresponse()
        html = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == 200
    assert "MUZAMMIL YOUNUS" in html
    assert "A1234567" in html
    assert "2031-05-20" in html
