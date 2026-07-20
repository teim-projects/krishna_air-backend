# Generated manually for visit amount split from AMC cost
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('amc', '0014_amcservicevisit'),
    ]

    operations = [
        migrations.AddField(
            model_name='amcservicevisit',
            name='amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Share of AMC cost for this visit (amc_cost / visit count).',
                max_digits=12,
            ),
        ),
    ]
