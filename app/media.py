import base64
import mimetypes
import os

MAX_TEXT_CHARS = 60000
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
TEXT_EXT = {".txt", ".md", ".csv", ".json", ".xml", ".html", ".py", ".js", ".css",
            ".log", ".ini", ".yaml", ".yml", ".sql", ".php", ".cs"}


def _pdf_text(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        return "[pypdf نصب نیست؛ متن این PDF خوانده نشد]"
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def load_attachment(path):
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    if ext in IMAGE_EXT:
        mime = mimetypes.guess_type(name)[0] or "image/png"
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return {"kind": "image", "name": name, "url": f"data:{mime};base64,{b64}"}
    if ext == ".pdf":
        text = _pdf_text(path)
    elif ext in TEXT_EXT or ext == "":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        raise ValueError(f"نوع فایل پشتیبانی نمی‌شود: {ext}")
    return {"kind": "text", "name": name, "text": text[:MAX_TEXT_CHARS]}


def build_user_content(text, attachments):
    """Return a plain string, or a list of content parts when images are attached."""
    if not attachments:
        return text
    body = text
    for a in attachments:
        if a["kind"] == "text":
            body += f"\n\n--- فایل: {a['name']} ---\n{a['text']}"
    images = [a for a in attachments if a["kind"] == "image"]
    if not images:
        return body
    parts = [{"type": "text", "text": body or "این تصویر رو بررسی کن."}]
    parts += [{"type": "image_url", "image_url": {"url": a["url"]}} for a in images]
    return parts
