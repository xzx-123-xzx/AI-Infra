from pathlib import Path

from pypdf import PdfReader

from common.logger import my_logger


def parse_file(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    my_logger.info("Parsing file: %s", path.name)

    if suffix in {".txt", ".md", ".markdown", ".csv", ".json"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    raise ValueError(f"Unsupported file type: {suffix}")
