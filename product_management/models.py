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
  year_of_manufacture = models.IntegerField(blank=True, null=True)
  is_part = models.BooleanField(default=False)
  part_name = models.CharField(max_length=200, blank=True, null=True)
  model_no_idu = models.CharField(max_length=200, blank=True, null=True)
  model_no_odu = models.CharField(max_length=200, blank=True, null=True)
  description = models.TextField(blank=True, null=True)


  def __str__(self):
        inverter_text = "Inverter" if self.inverter else "Non-Inverter"
        return f"{self.model_no}-{inverter_text}-{self.phase}"
  


class ProductVariant(models.Model):
  product_model = models.ForeignKey(ProductModel, on_delete=models.CASCADE, related_name='variants')
  capacity = models.CharField(max_length=50)
  star_rating = models.IntegerField()
 
  sku = models.CharField(max_length=100 , unique=True, blank=True)
  mrp = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  dp = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
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
   

  
# Low side models for parts and accessories can be added here in the future as needed.


# Helper functions for item code generation can be added here as well.
def get_code_part(name: str):
    if not name:
        return ""

    parts = name.strip().upper().split()
    if len(parts) == 1:
        return parts[0][:2]   # first 2 letters if single word
    else:
        return "".join(p[0] for p in parts)  # first letter of each word



class material_type(models.Model):
   name = models.CharField(max_length=100)
   
   def __str__(self):
    return self.name
   
class item_type(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
      return self.name


class feature_type(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
      return self.name
    
class item_class(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
      return self.name
    
class item(models.Model):
    item_code = models.CharField(max_length=100,unique=True, blank=True)
    material_type_id = models.ForeignKey(material_type, on_delete=models.CASCADE, related_name='items')
    item_type_id = models.ForeignKey(item_type, on_delete=models.CASCADE, related_name='items')
    feature_type_id = models.ForeignKey(feature_type, on_delete=models.CASCADE, related_name='items')
    item_class_id = models.ForeignKey(item_class, on_delete=models.CASCADE, related_name='items')
    size = models.CharField(max_length=50, blank=True, null=True)
    size_unit = models.CharField(max_length=20, blank=True, null=True)
    thickness = models.CharField(max_length=50, blank=True, null=True)
    thickness_unit = models.CharField(max_length=20, blank=True, null=True)
    density = models.CharField(max_length=50, blank=True, null=True)
    density_unit = models.CharField(max_length=20, blank=True, null=True)
    brand = models.ForeignKey(brand, on_delete=models.CASCADE, related_name='items')
    description = models.TextField(blank=True, null=True)
    

    def generate_item_code(self):
        parts = [
            get_code_part(self.material_type_id.name),
            get_code_part(self.item_type_id.name),
            get_code_part(self.feature_type_id.name),
        ]

        if self.size:
            size_part = f"{self.size}{self.size_unit or ''}".upper()
            parts.append(size_part)

        if self.thickness:
            thickness_part = f"{self.thickness}{self.thickness_unit or ''}".upper()
            parts.append(thickness_part)

        parts.append(get_code_part(self.item_class_id.name))

        return "-".join(parts)

    def save(self, *args, **kwargs):
      if not self.item_code:
          base_code = self.generate_item_code()
          code = base_code
          i = 1
          while item.objects.filter(item_code=code).exists():
              code = f"{base_code}-{i}"
              i += 1
          self.item_code = code
      super().save(*args, **kwargs)

    def __str__(self):
        return self.item_code
