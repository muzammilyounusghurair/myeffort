from __future__ import annotations

import io
import re
from datetime import date, datetime
from pathlib import Path

from passport_agent.models import Attachment, PassportData


class PassportExtractionError(ValueError):
    """Raised when a passport document cannot be parsed with enough confidence."""


class PassportExtractor:
    """Extract passport fields from text, PDFs with text layers, and OCR-capable images."""

    _PASSPORT_NUMBER_RE = re.compile(
        r"(?:passport|document)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9]{5,12})",
        re.IGNORECASE,
    )
    _NAME_RE = re.compile(
        r"(?:full\s+name|name)\s*[:\-]?\s*([^\r\n]{3,80})",
        re.IGNORECASE,
    )
    _EXPIRY_RE = re.compile(
        r"(?:date\s+of\s+expiry|expiry\s+date|expiration\s+date|expires)\s*[:\-]?\s*"
        r"([0-9]{1,4}[./\-\s][A-Za-z0-9]{1,9}[./\-\s][0-9]{2,4}|[0-9]{6})",
        re.IGNORECASE,
    )
    _MRZ_CHARS_RE = re.compile(r"^[A-Z0-9<]{30,}$")

    def extract_attachment(self, attachment: Attachment) -> PassportData:
        return self.extract(
            payload=attachment.payload,
            filename=attachment.filename,
            content_type=attachment.content_type,
        )

    def extract(self, payload: bytes, filename: str, content_type: str = "") -> PassportData:
        text = self._extract_text(payload, filename, content_type)
        data = self._extract_from_text(text, filename)
        if data is None:
            raise PassportExtractionError(
                "Could not extract name, passport number, and expiry date from the supplied file."
            )
        return data

    def _extract_text(self, payload: bytes, filename: str, content_type: str) -> str:
        suffix = Path(filename).suffix.lower()
        normalized_type = content_type.lower()

        if suffix == ".pdf" or normalized_type == "application/pdf":
            return self._extract_pdf_text(payload)

        if normalized_type.startswith("image/") or suffix in {
            ".bmp",
            ".gif",
            ".jpeg",
            ".jpg",
            ".png",
            ".tiff",
            ".webp",
        }:
            return self._extract_image_text(payload)

        return self._decode_text(payload)

    def _extract_pdf_text(self, payload: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise PassportExtractionError(
                "PDF extraction requires the pypdf package to be installed."
            ) from exc

        reader = PdfReader(io.BytesIO(payload))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(page for page in pages if page.strip())
        if not text.strip():
            raise PassportExtractionError(
                "No text was found in the PDF. Use OCR for scanned passport images."
            )
        return text

    def _extract_image_text(self, payload: bytes) -> str:
        try:
            from PIL import Image
            import pytesseract
        except ImportError as exc:
            raise PassportExtractionError(
                "Image extraction requires optional OCR dependencies: Pillow and pytesseract."
            ) from exc

        image = Image.open(io.BytesIO(payload))
        text = pytesseract.image_to_string(image)
        if not text.strip():
            raise PassportExtractionError("OCR did not return any text from the image.")
        return text

    def _decode_text(self, payload: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return payload.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise PassportExtractionError("File is not readable text, PDF, or OCR-capable image.")

    def _extract_from_text(self, text: str, filename: str) -> PassportData | None:
        mrz_data = self._extract_from_mrz(text, filename)
        labelled_data = self._extract_from_labelled_text(text, filename)

        if mrz_data and labelled_data:
            return PassportData(
                full_name=labelled_data.full_name or mrz_data.full_name,
                passport_number=labelled_data.passport_number or mrz_data.passport_number,
                expiry_date=labelled_data.expiry_date or mrz_data.expiry_date,
                source_file=filename,
                confidence=max(mrz_data.confidence or 0.0, labelled_data.confidence or 0.0),
            )
        return labelled_data or mrz_data

    def _extract_from_labelled_text(self, text: str, filename: str) -> PassportData | None:
        name_match = self._NAME_RE.search(text)
        number_match = self._PASSPORT_NUMBER_RE.search(text)
        expiry_match = self._EXPIRY_RE.search(text)

        if not (name_match and number_match and expiry_match):
            return None

        expiry_date = self._parse_date(expiry_match.group(1))
        if expiry_date is None:
            return None

        return PassportData(
            full_name=self._normalize_name(name_match.group(1)),
            passport_number=number_match.group(1).upper(),
            expiry_date=expiry_date,
            source_file=filename,
            confidence=0.75,
        )

    def _extract_from_mrz(self, text: str, filename: str) -> PassportData | None:
        lines = [
            self._normalize_mrz_line(line)
            for line in text.splitlines()
            if self._normalize_mrz_line(line)
        ]

        for first, second in zip(lines, lines[1:]):
            if not first.startswith("P<") or len(first) < 30 or len(second) < 30:
                continue
            first = first.ljust(44, "<")[:44]
            second = second.ljust(44, "<")[:44]

            passport_number = second[:9].replace("<", "").strip()
            expiry_date = self._parse_mrz_expiry(second[21:27])
            full_name = self._parse_mrz_name(first[5:44])

            if passport_number and expiry_date and full_name:
                return PassportData(
                    full_name=full_name,
                    passport_number=passport_number,
                    expiry_date=expiry_date,
                    source_file=filename,
                    confidence=0.9,
                )

        return None

    def _normalize_mrz_line(self, value: str) -> str:
        normalized = re.sub(r"\s+", "", value.upper())
        return normalized if self._MRZ_CHARS_RE.match(normalized) else ""

    def _parse_mrz_name(self, mrz_name: str) -> str:
        parts = mrz_name.strip("<").split("<<", maxsplit=1)
        surname = parts[0].replace("<", " ").strip()
        given_names = parts[1].replace("<", " ").strip() if len(parts) > 1 else ""
        return self._normalize_name(f"{given_names} {surname}".strip())

    def _parse_mrz_expiry(self, value: str) -> date | None:
        if not re.fullmatch(r"\d{6}", value):
            return None

        year = 2000 + int(value[:2])
        current_year = date.today().year
        if year > current_year + 30:
            year -= 100

        try:
            return date(year, int(value[2:4]), int(value[4:6]))
        except ValueError:
            return None

    def _parse_date(self, value: str) -> date | None:
        cleaned = " ".join(value.strip().replace(",", " ").split())
        formats = (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y.%m.%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%d.%m.%Y",
            "%d %m %Y",
            "%d %b %Y",
            "%d %B %Y",
            "%d-%b-%Y",
            "%d-%B-%Y",
            "%d/%b/%Y",
            "%d/%B/%Y",
            "%y%m%d",
        )

        for fmt in formats:
            try:
                parsed = datetime.strptime(cleaned, fmt).date()
                if fmt == "%y%m%d" and parsed.year > date.today().year + 30:
                    parsed = date(parsed.year - 100, parsed.month, parsed.day)
                return parsed
            except ValueError:
                continue
        return None

    def _normalize_name(self, value: str) -> str:
        normalized = re.sub(r"\s+", " ", value.replace("\n", " ")).strip(" .,'-")
        return normalized.upper()
