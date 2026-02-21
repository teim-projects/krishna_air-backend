from .models import acType , acSubTypes , brand , ProductModel , ProductVariant, ProductInventory, material_type, item_type, item_class, feature_type, item
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
        source='ac_sub_type_id.name',
        read_only=True
    )
    ac_type_id = serializers.IntegerField(source='ac_sub_type_id.ac_type_id.id', read_only=True)
    ac_type_name = serializers.CharField(source='ac_sub_type_id.ac_type_id.name', read_only=True)
    brand_name = serializers.CharField(
        source='brand_id.name',
        read_only=True
    )

    model = serializers.SerializerMethodField()

    class Meta:
        model = ProductModel
        fields = '__all__'

    def get_model(self, obj):
        inverter_text = "Inverter" if obj.inverter else "Non-Inverter"
        return f"{obj.model_no}-{inverter_text}-{obj.phase}"
    


class productVariantSerializer(serializers.ModelSerializer):
  model_name = serializers.CharField(
    source = "product_model.name",
    read_only = True
  )
   
  class Meta:
    model = ProductVariant
    fields = '__all__'

class productInventorySerializer(serializers.ModelSerializer):
  sku = serializers.CharField(
    source = 'product_variant.sku',
    read_only = True
  )
  class Meta:
    model = ProductInventory
    fields = '__all__'

class MaterialTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = material_type
        fields = '__all__'


class ItemTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = item_type
        fields = '__all__'


class ItemClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = item_class
        fields = '__all__'


class FeatureTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = feature_type
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    item_type_name = serializers.CharField(
        source='item_type_id.name',
        read_only=True
    )
    item_class_name = serializers.CharField(
        source='item_class_id.name',
        read_only=True
    )
    material_type_name = serializers.CharField(
        source='material_type_id.name',
        read_only=True
    )
    feature_type_name = serializers.CharField(
        source='feature_type_id.name',
        read_only=True
    )
    brand_name = serializers.CharField(
        source='brand.name',
        read_only=True
    )

    class Meta:
        model = item
        fields = '__all__'