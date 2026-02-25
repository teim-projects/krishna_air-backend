from rest_framework import serializers
from .models import Vendor


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'
    
    def validate_mobile(self, value):
        """Validate mobile number is 10 digits"""
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Mobile number must be 10 digits")
        return value
    
    def validate_gst_details(self, value):
        """Validate GST number is 15 characters"""
        if len(value) != 15:
            raise serializers.ValidationError("GST number must be 15 characters")
        return value
    
    def validate_pan_details(self, value):
        """Validate PAN number is 10 characters"""
        if value and len(value) != 10:
            raise serializers.ValidationError("PAN number must be 10 characters")
        return value
    
    def validate_office_poc_phone(self, value):
        """Validate office POC phone is 10 digits"""
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Phone number must be 10 digits")
        return value
