from rest_framework import serializers

from .models import SlidingImage


class SlidingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlidingImage
        fields = ["id", "image", "caption", "order", "is_active"]
