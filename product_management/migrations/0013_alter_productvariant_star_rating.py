from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_management', '0012_alter_productmodel_phase'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productvariant',
            name='star_rating',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
