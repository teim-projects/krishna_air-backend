from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Customer, lead_management

class CustomerSerializer(serializers.ModelSerializer):
   class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ('id',)