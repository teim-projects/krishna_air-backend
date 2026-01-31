from django.db import models
import uuid


class acType(models.Model):
  name = models.CharField(max_length=100)
  description = models.TextField(blank=True, null=True)

  def __str__(self):
    return self.name
  
class acSubTypes(models.Model):
  ac_type_id = models.ForeignKey(acType, on_delete=models.CASCADE, related_name="sub_types") 
  name = models.CharField(max_length=100)
  description = models.TextField(blank=True, null=True)
  
  def __str__(self):
    return self.name

class brand(models.Model):
  name = models.CharField(max_length=100)
  desc = models.TextField(blank=True, null=True)
  
  def __str__(self):
    return self.name

class ProductModel(models.Model):
  name = models.CharField(max_length=100)
  ac_sub_type_id = models.ForeignKey(acSubTypes, on_delete=models.CASCADE, related_name='product_model')
  brand_id = models.ForeignKey(brand, on_delete=models.CASCADE, related_name='product_model' )
  model_no = models.CharField(max_length=200)
  phase = models.CharField(max_length=20)
  inverter = models.BooleanField(default=False)
  is_active = models.BooleanField(default=True)
  description = models.TextField(blank=True, null=True)

  
  def __str__(self):
        inverter_text = "Inverter" if self.inverter else "Non-Inverter"
        return f"{self.model_no}-{inverter_text}-{self.phase}"
  


class ProductVariant(models.Model):
  product_model = models.ForeignKey(ProductModel, on_delete=models.CASCADE, related_name='variants')
  capacity = models.CharField(max_length=50)
  star_rating = models.IntegerField()
  price = models.DecimalField(max_digits=10, decimal_places=2)
  sku = models.CharField(max_length=100 , unique=True, blank=True)
  is_active = models.BooleanField(default=True)

  def save(self, *args, **kwargs):
     if not self.sku:
        self.sku  = self.generate_sku()
     super().save(*args, **kwargs)  

  
  def generate_sku(self):
    """
        Example SKU:
        SAM-AR18-15-5-9F2A
    """

    brand_code = self.product_model.brand_id.name[:3].upper()
    model_code = self.product_model.model_no[:5].upper()
    capacity_code = str(self.capacity).replace('.', '')
    star_code = str(self.star_rating)
    unique_code = uuid.uuid4().hex[:4].upper()
    
    return f"{brand_code}-{model_code}-{capacity_code}-{star_code}-{unique_code}"

  def __str__(self):
        return self.sku
  

INVENTORY_STATUS = [
            ('IN_STOCK', 'IN_STOCK'),
            ('SOLD', 'SOLD'),
            ('DAMAGED', 'DAMAGED'),
            ]

class ProductInventory(models.Model):
   product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='inventory')
   serial_no = models.CharField(max_length=200)
   status = models.CharField(max_length=20, choices=INVENTORY_STATUS, default="IN_STOCK")
   warehouse = models.CharField(max_length=200, blank=True, null=True)
   purchase_date = models.DateField(blank=True, null=True)
   warranty_start = models.DateField(blank=True, null=True)
   warranty_end = models.DateField(blank=True, null=True)
   
   def __str__(self):
    return f"{self.product_variant.sku}-{self.serial_no}"