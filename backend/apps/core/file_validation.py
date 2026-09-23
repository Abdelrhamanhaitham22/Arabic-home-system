from django.core.exceptions import ValidationError


FILE_SIGNATURES = {
    ".pdf": (b"%PDF",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def validate_uploaded_file(uploaded_file, allowed_extensions, error_message):
    extension = _file_extension(uploaded_file.name)
    if extension not in allowed_extensions:
        raise ValidationError(error_message)

    signatures = FILE_SIGNATURES.get(extension, ())
    header_size = max((len(signature) for signature in signatures), default=0)
    header = uploaded_file.read(header_size)
    uploaded_file.seek(0)
    if not any(header.startswith(signature) for signature in signatures):
        raise ValidationError(error_message)


def _file_extension(filename):
    return f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else ""


def validate_pdf_file(uploaded_file):
    validate_uploaded_file(
        uploaded_file,
        allowed_extensions={".pdf"},
        error_message="The uploaded file must be a valid PDF.",
    )


def validate_answer_file(uploaded_file):
    validate_uploaded_file(
        uploaded_file,
        allowed_extensions={".pdf", ".jpg", ".jpeg", ".png"},
        error_message="The uploaded file must be a valid PDF, JPEG, or PNG.",
    )
