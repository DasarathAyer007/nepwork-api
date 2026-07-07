import json


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
