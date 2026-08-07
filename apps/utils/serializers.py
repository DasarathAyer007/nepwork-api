import json

from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework import serializers

from apps.utils.html_sanitizer import sanitize_svg


class SvgIconUploadMixin:
    """Validates an uploaded category icon and falls back to a default SVG.

    Set `default_icon_path` (relative to MEDIA_URL) on the serializer to
    control which fallback icon is served when none is uploaded.
    """

    MAX_SIZE_KB = 512
    default_icon_path = "default/default.svg"

    def validate_icon(self, value):
        if value is None:
            return value

        if not value.name.lower().endswith(".svg"):
            raise serializers.ValidationError("Icon must be an SVG file.")

        if value.size and value.size > self.MAX_SIZE_KB * 1024:
            raise serializers.ValidationError(
                f"Icon must be under {self.MAX_SIZE_KB}KB."
            )

        try:
            raw_svg = value.read().decode("utf-8")
        except UnicodeDecodeError:
            raise serializers.ValidationError(
                "Icon file is not valid SVG text."
            )

        # Rendered inline by the public site, so scripts/handlers are
        # stripped here rather than trusting the uploading admin.
        sanitized_svg = sanitize_svg(raw_svg)
        if not sanitized_svg.strip():
            raise serializers.ValidationError("Icon file is not a valid SVG.")

        return ContentFile(sanitized_svg.encode("utf-8"), name=value.name)

    def to_representation(self, instance):
        data = super().to_representation(instance)  # pyright: ignore[reportAttributeAccessIssue]

        if not data.get("icon"):
            request = self.context.get("request")  # pyright: ignore[reportAttributeAccessIssue]
            url = settings.MEDIA_URL + self.default_icon_path
            data["icon"] = request.build_absolute_uri(url) if request else url

        return data


class MultipartJSONFieldsMixin:
    """Decodes JSON-encoded list strings for selected fields before validation.

    Multipart/form-data requests can't carry real arrays, so clients
    JSON.stringify() them into plain string fields. Set `json_fields` on
    the serializer to the ListField names that need decoding before DRF
    validates them.
    """

    json_fields = ()

    def to_internal_value(self, data):
        if self.json_fields:
            data = self._decode_json_fields(data)
        return super().to_internal_value(data)  # pyright: ignore[reportAttributeAccessIssue]

    def _decode_json_fields(self, data):
        data = data.copy() if hasattr(data, "_mutable") else dict(data)

        for field in self.json_fields:
            value = data.get(field)
            if not isinstance(value, str) or not value:
                continue
            try:
                parsed = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                continue

            setlist = getattr(data, "setlist", None)
            if isinstance(parsed, list) and setlist is not None:
                # ListField reads QueryDict values via getlist(), so the
                # decoded items must be stored individually rather than
                # as one entry wrapping the whole list.
                setlist(field, parsed)
            else:
                data[field] = parsed
        return data
