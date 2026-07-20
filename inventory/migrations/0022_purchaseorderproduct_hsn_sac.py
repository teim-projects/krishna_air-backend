from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0021_deliverychallan_destination_and_partner_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorderproduct',
            name='hsn_sac',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
