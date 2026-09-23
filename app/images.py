import os
import uuid

from flask import current_app, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

IMAGE_CATEGORIES = ("fabrics", "patterns", "projects", "pieces")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {
    "",
    "application/octet-stream",
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/png",
    "image/webp",
}


def ensure_upload_directories():
    root = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(root, exist_ok=True)
    for category in IMAGE_CATEGORIES:
        os.makedirs(os.path.join(root, category), exist_ok=True)


def clear_uploaded_files():
    root = current_app.config["UPLOAD_FOLDER"]
    if not os.path.isdir(root):
        return
    for category in IMAGE_CATEGORIES:
        directory = os.path.join(root, category)
        if not os.path.isdir(directory):
            continue
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                os.remove(path)


def _claimed_extension(filename):
    safe_name = secure_filename(filename or "")
    if not safe_name or "." not in safe_name:
        return ""
    return "." + safe_name.rsplit(".", 1)[-1].lower()


def _read_header(file_storage, size=16):
    stream = file_storage.stream
    position = stream.tell()
    header = stream.read(size)
    stream.seek(position)
    return header


def _detect_extension(header):
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    return None


def _file_size(file_storage):
    stream = file_storage.stream
    position = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(position)
    return size


def validate_image_file(file_storage):
    """Return a safe extension, None if no file was provided, or raise ValueError."""
    if file_storage is None or not isinstance(file_storage, FileStorage):
        return None
    filename = (file_storage.filename or "").strip()
    if not filename:
        return None

    claimed = _claimed_extension(filename)
    if claimed not in ALLOWED_EXTENSIONS:
        raise ValueError("Use a JPG, PNG, or WebP image.")

    mime = (file_storage.mimetype or "").lower()
    if mime not in ALLOWED_MIME_TYPES:
        raise ValueError("Use a JPG, PNG, or WebP image.")

    header = _read_header(file_storage, 16)
    detected = _detect_extension(header)
    if detected is None:
        raise ValueError("That file is not a valid JPG, PNG, or WebP image.")

    jpeg_claimed = claimed in {".jpg", ".jpeg"}
    if jpeg_claimed and detected != ".jpg":
        raise ValueError("That file is not a valid JPG, PNG, or WebP image.")
    if not jpeg_claimed and claimed != detected:
        raise ValueError("That file is not a valid JPG, PNG, or WebP image.")

    max_bytes = current_app.config.get("MAX_IMAGE_BYTES", 5 * 1024 * 1024)
    size = _file_size(file_storage)
    if size == 0:
        raise ValueError("That file is not a valid JPG, PNG, or WebP image.")
    if size > max_bytes:
        raise ValueError("That image is too large. Please use a file under 5 MB.")
    return detected


def save_uploaded_image(file_storage, category):
    if category not in IMAGE_CATEGORIES:
        raise ValueError("Unsupported image category.")
    extension = validate_image_file(file_storage)
    if extension is None:
        return None

    ensure_upload_directories()
    filename = f"{uuid.uuid4().hex}{extension}"
    destination = os.path.join(
        current_app.config["UPLOAD_FOLDER"], category, filename
    )
    file_storage.stream.seek(0)
    file_storage.save(destination)
    return f"{category}/{filename}"


def is_stored_upload(image_url):
    if not image_url or image_url.startswith(("http://", "https://", "/")):
        return False
    category, separator, filename = image_url.partition("/")
    if not separator or category not in IMAGE_CATEGORIES:
        return False
    if not filename or filename != os.path.basename(filename):
        return False
    if filename.startswith(".") or ".." in filename:
        return False
    return True


def image_is_referenced(image_url):
    from app.models import Fabric, Pattern, PatternPiece, Project

    if not image_url:
        return False
    return any(
        model.query.filter_by(image_url=image_url).first() is not None
        for model in (Fabric, Pattern, PatternPiece, Project)
    )


def delete_local_image(image_url):
    if not is_stored_upload(image_url) or image_is_referenced(image_url):
        return
    category, _, filename = image_url.partition("/")
    directory = os.path.realpath(
        os.path.join(current_app.config["UPLOAD_FOLDER"], category)
    )
    path = os.path.realpath(os.path.join(directory, filename))
    if path != directory and not path.startswith(directory + os.sep):
        return
    if os.path.isfile(path):
        os.remove(path)


def replace_image(record, file_storage, category):
    """Attach a newly uploaded image. Return the previous path to delete after commit."""
    new_path = save_uploaded_image(file_storage, category)
    if not new_path:
        return None
    previous = record.image_url
    record.image_url = new_path
    return previous


def project_image_ref(project):
    if project is None:
        return None
    if project.image_url:
        return project.image_url
    pattern = getattr(project, "pattern", None)
    if pattern is not None and pattern.image_url:
        return pattern.image_url
    outer = getattr(project, "outer_fabric", None)
    if outer is not None and outer.image_url:
        return outer.image_url
    return None


def public_image_url(image_url):
    if not image_url:
        return ""
    if image_url.startswith(("http://", "https://")):
        return image_url
    if not is_stored_upload(image_url):
        return ""
    category, _, filename = image_url.partition("/")
    return url_for("uploaded_file", category=category, filename=filename)
