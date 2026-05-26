from app.core.config import settings
from app.models.enums import EntityType
from app.utils.slug import safe_filename, slugify


def build_stem_object_key(
    *,
    class_name: str,
    entity_type: EntityType,
    entity_name: str,
    original_filename: str,
) -> str:
    """
    Layout chốt hiện tại:

    Google Drive logical path:
            STEM/{classSlug}/{entityType}/{entitySlug}/{fileName}

    Ví dụ:
            STEM/lop-11/documents/binh-loc-nuoc/hoa-11-binh-loc-nuoc.docx
    """
    parts: list[str] = []

    root_prefix = settings.STORAGE_ROOT_PREFIX.strip("/").strip()
    if root_prefix:
        parts.append(root_prefix)

    parts.extend(
        [
            slugify(class_name),
            entity_type.value,
            slugify(entity_name),
            safe_filename(original_filename),
        ]
    )
    return "/".join(parts)
