"""Turn a source (PDF, URL) into clean plain text. Pure logic — no Streamlit."""

import trafilatura
from pypdf import PdfReader


def extract_pdf_text(uploaded_file):
    """Pull text out of an uploaded PDF. Returns '' if there's no text layer."""
    reader = PdfReader(uploaded_file)
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def extract_url_text(url):
    """Fetch an article URL and extract its main text. Returns '' on failure."""
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        return ""
    return trafilatura.extract(downloaded) or ""