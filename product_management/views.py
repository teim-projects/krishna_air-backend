from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework import status , filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import *
from .serializers import * 


class acTypeViewSet(ModelViewSet):
    queryset = acType.objects.all()
    serializer_class = acTypeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields  = ['name']



class acSubTypesViewSet(ModelViewSet):
    queryset = acSubTypes.objects.all()
    serializer_class = acSubTypesSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ac_type_id']
    search_fields  = ['name']




class brandViewSet(ModelViewSet):
    queryset = brand.objects.all()
    serializer_class = brandSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields  = ['name']


class productModelViewSet(ModelViewSet):
    queryset = ProductModel.objects.all()
    serializer_class = productModelSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
    'brand_id',
    'ac_sub_type_id',      # ✅ ADD THIS
    'ac_sub_type_id__ac_type_id',
    'is_active',
    'inverter',
    'phase'
]
    search_fields  = ['name','model_no']

class productVariabtViewSet(ModelViewSet):
    queryset = ProductVariant.objects.all()
    serializer_class = productVariantSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active','product_model__inverter','product_model__phase','product_model']
    search_fields  = ['sku','capacity']


class productInventoryViewSet(ModelViewSet):
    queryset = ProductInventory.objects.all()
    serializer_class = productInventorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 
                        'purchase_date',
                        'product_variant__product_model__brand_id__name'
                        ]
    
    search_fields  = ['serial_no',
                      'product_variant__sku',
                      'product_variant__capacity'
                      ]



class material_typeViewSet(ModelViewSet):
    queryset = material_type.objects.all()
    serializer_class = MaterialTypeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields  = ['name']
    pagination_class = None  # Disable pagination for lookup tables

class item_typeViewSet(ModelViewSet):
    queryset = item_type.objects.all()
    serializer_class = ItemTypeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields  = ['name']
    pagination_class = None  # Disable pagination for lookup tables

class item_classViewSet(ModelViewSet):
    queryset = item_class.objects.all()
    serializer_class = ItemClassSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields  = ['name']
    pagination_class = None  # Disable pagination for lookup tables

class feature_typeViewSet(ModelViewSet):
    queryset = feature_type.objects.all()
    serializer_class = FeatureTypeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields  = ['name']
    pagination_class = None  # Disable pagination for lookup tables

class itemViewSet(ModelViewSet):
    queryset = item.objects.all()
    serializer_class = ItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['item_type_id','item_class_id','material_type_id','feature_type_id']
    search_fields  = ['=item_code']
    
    def get_paginated_response(self, data):
        """Override to return all items when requested via query param"""
        if self.request.query_params.get('all') == 'true':
            return Response(data)
        return super().get_paginated_response(data)
    
    def paginate_queryset(self, queryset):
        """Skip pagination when 'all=true' is in query params"""
        if self.request.query_params.get('all') == 'true':
            return None
        return super().paginate_queryset(queryset)
  
  
class ACTypeMaterialViewSet(ModelViewSet):
    queryset = AcMaterials.objects.select_related('ac_type', 'material')
    serializer_class = AcMaterialSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['ac_type__name']
    filterset_fields = ['ac_type']
    pagination_class = None  # Disable pagination to return all materials
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objs = serializer.save()

        return Response(
            {
                "message": "Materials mapped successfully",
                "created_count": len(objs)
            },
            status=status.HTTP_201_CREATED
        )

    # 🔥 BULK UPDATE (REPLACE)
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        ac_type_id = request.data.get('ac_type')
        material_ids = request.data.get('material', [])

        if not ac_type_id:
            return Response({"error": "ac_type is required"}, status=400)

        # remove duplicates
        material_ids = list(set(material_ids))

        # 🔴 Step 1: delete old mappings
        AcMaterials.objects.filter(ac_type_id=ac_type_id).delete()

        # 🟢 Step 2: create new mappings
        objs = [
            AcMaterials(ac_type_id=ac_type_id, material_id=mid)
            for mid in material_ids
        ]

        AcMaterials.objects.bulk_create(objs)

        return Response({
            "message": "Materials updated successfully",
            "updated_count": len(objs)
        }, status=status.HTTP_200_OK)


# ================= SMART PRODUCT SEARCH API =================
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def product_search_all(request):
    """
    Single endpoint that returns all product variants with combined searchable text
    """
    try:
        search_query = request.GET.get('search', '').strip()
        
        # Get all product variants with related data
        queryset = ProductVariant.objects.select_related(
            'product_model__brand_id',
            'product_model__ac_sub_type_id__ac_type_id',
            'product_model__ac_sub_type_id'
        ).filter(is_active=True)
        
        # If search query provided, filter results
        if search_query:
            queryset = queryset.filter(
                Q(product_model__brand_id__name__icontains=search_query) |
                Q(product_model__name__icontains=search_query) |
                Q(sku__icontains=search_query) |
                Q(product_model__ac_sub_type_id__name__icontains=search_query) |
                Q(product_model__ac_sub_type_id__ac_type_id__name__icontains=search_query) |
                Q(capacity__icontains=search_query)
            )
        
        # Limit results to prevent performance issues
        queryset = queryset[:50]
        
        # Format response with combined display text
        results = []
        for variant in queryset:
            try:
                # Safely get brand name
                brand_name = variant.product_model.brand_id.name if variant.product_model and variant.product_model.brand_id else 'Unknown Brand'
                model_name = variant.product_model.name if variant.product_model else 'Unknown Model'
                
                # Create combined display text
                display_text = f"{brand_name} {model_name}"
                
                if variant.capacity:
                    unit = variant.unit if variant.unit else ''
                    display_text += f" - {variant.capacity} {unit}"
                    
                # Safely get ac_sub_type
                if variant.product_model and variant.product_model.ac_sub_type_id:
                    display_text += f" {variant.product_model.ac_sub_type_id.name}"
                    
                    # Safely get ac_type
                    if variant.product_model.ac_sub_type_id.ac_type_id:
                        display_text += f" {variant.product_model.ac_sub_type_id.ac_type_id.name}"
                
                # Safely get ac_type_name and ac_sub_type_name
                ac_type_name = ''
                ac_sub_type_name = ''
                
                if variant.product_model and variant.product_model.ac_sub_type_id:
                    ac_sub_type_name = variant.product_model.ac_sub_type_id.name
                    if variant.product_model.ac_sub_type_id.ac_type_id:
                        ac_type_name = variant.product_model.ac_sub_type_id.ac_type_id.name
                
                result_item = {
                    'id': variant.id,
                    'sku': variant.sku,
                    'display_text': display_text,
                    'brand_name': brand_name,
                    'model_name': model_name,
                    'ac_type_name': ac_type_name,
                    'ac_sub_type_name': ac_sub_type_name,
                    'capacity': variant.capacity or '',
                    'variant_sku': variant.sku,
                }
                
                results.append(result_item)
                    
            except Exception as e:
                # Log the error but continue processing other variants
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error processing variant {variant.id}: {str(e)}")
                continue
        
        return Response(results)
        
    except Exception as e:
        # Log the full error for debugging
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error in product_search_all: {str(e)}\n{traceback.format_exc()}")
        
        # Return a proper error response
        return Response(
            {
                'error': 'An error occurred while searching products',
                'detail': str(e)
            },
            status=500
        )