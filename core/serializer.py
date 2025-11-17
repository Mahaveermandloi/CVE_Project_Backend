from rest_framework import serializers
from .models import CveChange

class CveChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CveChange
        fields = "__all__"
