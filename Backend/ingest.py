"""Build a reproducible, page-aware corpus from the three required arXiv PDFs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

import fitz


BASE_DIR = Path(__file__).resolve().parent
PAPERS_DIR = BASE_DIR / "data" / "papers"
INDEX_DIR = BASE_DIR / "data" / "index"
MANIFEST_PATH = PAPERS_DIR / "manifest.json"
CHUNKS_PATH = INDEX_DIR / "chunks.json"


@dataclass(frozen=True)
class PaperSpec:
    filename: str
    title: str
    arxiv_id: str
    version: int

    @property
    def marker(self) -> str:
        return f"arXiv:{self.arxiv_id}v{self.version}"


REQUIRED_PAPERS = (
    PaperSpec("attention u need.pdf", "Attention Is All You Need", "1706.03762", 7),
    PaperSpec("moshi_2410.00037v1.pdf", "Moshi: a speech-text foundation model for real-time dialogue", "2410.00037", 1),
    PaperSpec("dynamic chunking.pdf", "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling", "2507.07955", 2),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_text(text: str) -> str:
    """Normalize extraction whitespace without deleting equations or content."""
    text = text.replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)  # join PDF line-break hyphenation
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def section_for_page(text: str, previous: str = "Unsectioned") -> str:
    """Return the last plausible numbered section heading found on a page."""
    matches = re.findall(r"(?m)^\s*((?:\d+(?:\.\d+){0,3})\.?\s+[^\n]{3,120})$", text)
    return clean_text(matches[-1]) if matches else previous


def chunk_words(words: list[str], size: int, overlap: int) -> Iterable[list[str]]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size must be positive and overlap must be smaller than size")
    for start in range(0, len(words), size - overlap):
        current = words[start : start + size]
        if current:
            yield current
        if start + size >= len(words):
            break


def verify_paper(spec: PaperSpec) -> dict:
    path = PAPERS_DIR / spec.filename
    if not path.exists():
        raise FileNotFoundError(f"Required PDF is missing: {path}")
    with fitz.open(path) as pdf:
        first_page = pdf[0].get_text("text")
        if spec.marker not in first_page:
            raise ValueError(
                f"{path.name} is not the required version: expected {spec.marker}; "
                f"found first-page marker(s) {re.findall(r'arXiv:[^\s]+', first_page)}"
            )
        if spec.title.lower() not in first_page.lower():
            raise ValueError(f"{path.name} does not contain the expected title on page 1")
        return {
            **asdict(spec),
            "path": str(path.relative_to(BASE_DIR)).replace("\\", "/"),
            "sha256": sha256(path),
            "page_count": pdf.page_count,
            "first_page_marker": spec.marker,
        }


def build_manifest() -> list[dict]:
    verified = [verify_paper(spec) for spec in REQUIRED_PAPERS]
    # The originally supplied Moshi v2 is deliberately retained for auditability, never indexed.
    excluded = PAPERS_DIR / "speech text foundation.pdf"
    excluded_note: dict[str, str] | None = None
    if excluded.exists():
        with fitz.open(excluded) as pdf:
            markers = re.findall(r"arXiv:[^\s]+", pdf[0].get_text("text"))
        excluded_note = {
            "path": str(excluded.relative_to(BASE_DIR)).replace("\\", "/"),
            "sha256": sha256(excluded),
            "reason": "Supplied file identifies itself as arXiv:2410.00037v2; assignment requires v1.",
            "first_page_markers": markers,
        }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "verified_papers": verified,
        "excluded_files": [excluded_note] if excluded_note else [],
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return verified


def build_chunks(chunk_size: int = 500, overlap: int = 75, *, persist: bool = True) -> list[dict]:
    """Extract page-aware chunks, keeping page/section metadata on every passage."""
    verified = build_manifest()
    chunks: list[dict] = []
    for paper in verified:
        path = BASE_DIR / paper["path"]
        section = "Unsectioned"
        with fitz.open(path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                page_text = clean_text(page.get_text("text"))
                if not page_text:
                    continue
                section = section_for_page(page_text, section)
                words = page_text.split()
                for page_chunk_number, word_chunk in enumerate(chunk_words(words, chunk_size, overlap), start=1):
                    chunks.append(
                        {
                            "chunk_id": f"{paper['arxiv_id'].replace('.', '_')}_v{paper['version']}_p{page_number:02d}_c{page_chunk_number:02d}",
                            "text": " ".join(word_chunk),
                            "paper_title": paper["title"],
                            "arxiv_id": paper["arxiv_id"],
                            "version": paper["version"],
                            "pdf_page": page_number,
                            "section": section,
                            "source_file": paper["path"],
                            "content_sha256": paper["sha256"],
                        }
                    )
    if persist:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        CHUNKS_PATH.write_text(json.dumps(chunks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return chunks


if __name__ == "__main__":
    generated = build_chunks()
    print(f"Built {len(generated)} chunks at {CHUNKS_PATH}")
