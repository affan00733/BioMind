"""
File utilities for handling uploaded documents and extracting text content.

Supports common formats: .txt, .pdf, .docx. Falls back to best-effort decoding.
"""

from __future__ import annotations

from typing import Optional

import io
import os


def _extract_text_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader  # lazy import
    except Exception:
        return ""
    try:
        reader = PdfReader(io.BytesIO(content))
        texts = []
        for page in reader.pages:
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            if txt:
                texts.append(txt)
        return "\n\n".join(texts).strip()
    except Exception:
        return ""


def _extract_text_docx(content: bytes) -> str:
    try:
        import docx  # python-docx
    except Exception:
        return ""
    try:
        bio = io.BytesIO(content)
        document = docx.Document(bio)
        paras = [p.text for p in document.paragraphs if p.text]
        return "\n".join(paras).strip()
    except Exception:
        return ""


def _extract_text_txt(content: bytes) -> str:
    # Try utf-8 then latin-1 as a permissive fallback
    try:
        return content.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return content.decode("latin-1", errors="ignore")
        except Exception:
            return ""


def extract_text_from_file(filename: Optional[str], content: bytes) -> str:
    """
    Extract plain text from a file based on its extension.

    Args:
        filename: Original file name (used for extension detection)
        content: Raw file bytes

    Returns:
        Best-effort extracted text (may be empty string if unsupported)
    """
    ext = (os.path.splitext(filename or "")[1] or "").lower()
    if ext == ".pdf":
        text = _extract_text_pdf(content)
        if text:
            return text
        # fall back to raw decode
        return _extract_text_txt(content)
    if ext in {".docx"}:
        text = _extract_text_docx(content)
        if text:
            return text
        return _extract_text_txt(content)
    if ext in {".txt", ".md", ".csv", ".log"}:
        return _extract_text_txt(content)

    # Unknown extension: try text decode
    return _extract_text_txt(content)
