from .models import acType , acSubTypes , brand , ProductModel , ProductVariant, ProductInventory, material_type, item_type, item_class, feature_type, item, AcMaterials
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

    variant_sku = serializers.CharField(source="sku", read_only=True)

    ac_type_name = serializers.CharField(
        source="product_model.ac_sub_type_id.ac_type_id.name",
        read_only=True
    )

    ac_sub_type_name = serializers.CharField(
        source="product_model.ac_sub_type_id.name",
        read_only=True
    )

    brand_name = serializers.CharField(
        source="product_model.brand_id.name",
        read_only=True
    )

    model_no = serializers.CharField(
        source="product_model.model_no",
        read_only=True
    )

    class Meta:
        model = ProductVariant
        fields = "__all__"

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
    item_class_name = serializers.SerializerMethodField()
    feature_type_name = serializers.SerializerMethodField()
    
    material_type_name = serializers.CharField(
        source='material_type_id.name',
        read_only=True
    )
    brand_name = serializers.CharField(
        source='brand.name',
        read_only=True
    )

    class Meta:
        model = item
        fields = '__all__'

    def get_item_class_name(self, obj):
        return obj.item_class_id.name if obj.item_class_id else None

    def get_feature_type_name(self, obj):
        return obj.feature_type_id.name if obj.feature_type_id else None


class AcMaterialSerializer(serializers.ModelSerializer):
    # WRITE
    material = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )

    # READ
    ac_type_name = serializers.CharField(source='ac_type.name', read_only=True)
    material_id = serializers.IntegerField(source='material.id', read_only=True)
    material_name = serializers.SerializerMethodField()

    class Meta:
        model = AcMaterials
        fields = [
            'id',
            'ac_type',
            'material',
            'material_id',
            'material_name',
            'ac_type_name'
        ]

    def get_material_name(self, obj):
        item = obj.material

        parts = [
            item.material_type_id.name if item.material_type_id else "",
            item.item_type_id.name if item.item_type_id else "",
            item.feature_type_id.name if item.feature_type_id else "",
            item.item_class_id.name if item.item_class_id else "",
        ]

        # remove empty values
        parts = [p for p in parts if p]

        return " ".join(parts)
        
    def create(self, validated_data):
        ac_type = validated_data.get('ac_type')
        material_ids = validated_data.pop('material', [])

        material_ids = list(set(material_ids))

        existing = set(
            AcMaterials.objects.filter(
                ac_type=ac_type,
                material_id__in=material_ids
            ).values_list('material_id', flat=True)
        )

        objs = [
            AcMaterials(ac_type=ac_type, material_id=mid)
            for mid in material_ids if mid not in existing
        ]

        AcMaterials.objects.bulk_create(objs)
        return objs