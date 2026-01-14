from .models import acType , acSubTypes , brand
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class acTypeSerializer(serializers.ModelSerializer):
  
  class Meta:
    model = acType
    fields = '__all__'


class acSubTypesSerializer(serializers.ModelSerializer):
  
  class Meta:
    model = acSubTypes
    fields = '__all__'


class brandSerializer(serializers.ModelSerializer):
  
  class Meta:
    model = brand
    fields = '__all__'