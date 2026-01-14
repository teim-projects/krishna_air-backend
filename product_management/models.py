from django.db import models

class acType(models.Model):
  name = models.CharField(max_length=100)
  description = models.TextField(blank=True, null=True)


  
class acSubTypes(models.Model):
  ac_type_id = models.ForeignKey(acType, on_delete=models.CASCADE, related_name="sub_types") 
  name = models.CharField(max_length=100)
  description = models.TextField(blank=True, null=True)


class brand(models.Model):
  name = models.CharField(max_length=100)
  desc = models.TextField(blank=True, null=True)