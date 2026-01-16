from .models import acType , acSubTypes , brand , ProductModel , ProductVariant, ProductInventory
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class acTypeSerializer(serializers.ModelSerializer):
  
  class Meta:
    model = acType
    fields = '__all__'


class acSubTypesSerializer(serializers.ModelSerializer):
  ac_type_name =serializers.CharField(
    source = 'ac_type_id.name',
    read_only = True
  )
  class Meta:
    model = acSubTypes
    fields = '__all__'


class brandSerializer(serializers.ModelSerializer):
  
  class Meta:
    model = brand
    fields = '__all__'


class productModelSerializer(serializers.ModelSerializer):
  ac_sub_type_name = serializers.CharField(
    source = 'ac_sub_type_id.name',
    read_only = True
  )

  brand_name = serializers.CharField(
    source = "brand_id.name",
    read_only = True
  )

  class Meta:
    model = ProductModel
    fields = '__all__'

class productVariantSerializer(serializers.ModelSerializer):
  model_name = serializers.CharField(
    source = "product_model.name",
    read_only = True
  )
   
  class Meta:
    model = ProductVariant
    fields = '__all__'

class productInventorySerializer(serializers.ModelSerializer):

  class Meta:
    model = ProductInventory
    fields = '__all__'