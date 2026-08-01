from bleach import clean
from bleach.css_sanitizer import CSSSanitizer
from rest_framework import serializers

RICH_TEXT_ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "blockquote",
    "a",
]

RICH_TEXT_ALLOWED_ATTRIBUTES = {
    "a": ["href", "rel", "target"],
    "p": ["style"],
    "h1": ["style"],
    "h2": ["style"],
    "h3": ["style"],
}

RICH_TEXT_ALLOWED_STYLES = ["text-align"]

RICH_TEXT_CSS_SANITIZER = CSSSanitizer(
    allowed_css_properties=RICH_TEXT_ALLOWED_STYLES
)

RICH_TEXT_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_rich_text(value: str) -> str:
    """Strip a simple rich-text HTML fragment down to the tags/attributes/
    styles our editor (RichTextEditor) and viewer (RichTextViewer) support."""
    return clean(
        value,
        tags=RICH_TEXT_ALLOWED_TAGS,
        attributes=RICH_TEXT_ALLOWED_ATTRIBUTES,
        protocols=RICH_TEXT_ALLOWED_PROTOCOLS,
        css_sanitizer=RICH_TEXT_CSS_SANITIZER,
        strip=True,
    )


def clean_and_validate_rich_text(
    value: str,
    *,
    min_length: int | None = 20,
    max_length: int | None = 3000,
) -> str:
    """Sanitize a rich-text HTML field and enforce length limits on its
    plain-text content. Intended for use in a serializer's `validate_<field>`.

    Raises `serializers.ValidationError` if the plain-text content is shorter
    than `min_length` or longer than `max_length` (either may be `None` to
    skip that check).
    """
    cleaned = sanitize_rich_text(value)

    text_only = clean(cleaned, tags=[], strip=True).strip()
    if min_length is not None and len(text_only) < min_length:
        raise serializers.ValidationError(
            f"Give a bit more detail (at least {min_length} characters)."
        )
    if max_length is not None and len(text_only) > max_length:
        raise serializers.ValidationError(
            f"Keep it under {max_length} characters."
        )

    return cleaned
