from django.db.models import Model
from django.utils.text import slugify


def generate_unique_slug(
    model: type[Model],
    value: str,
    slug_field: str = "slug",
) -> str:
    base_slug = slugify(value)
    slug = base_slug

    if not model.objects.filter(**{slug_field: slug}).exists():  # type: ignore[attr-defined]
        return slug

    counter = 1

    while True:
        slug = f"{base_slug}-{counter}"

        if not model.objects.filter(**{slug_field: slug}).exists():  # type: ignore[attr-defined]
            return slug

        counter += 1
