# Generated migration file

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0016_alter_materialreturn_return_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryitem',
            name='total_in_quantity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='inventoryitem',
            name='total_out_quantity',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
