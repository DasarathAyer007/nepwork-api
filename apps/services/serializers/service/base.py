from rest_framework import serializers

from ...models import Service


class ServiceRadiusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["radius_km"]


class ServicePricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["price", "price_type", "currency"]
