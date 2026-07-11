from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('amc', '0004_alter_servicemanagementrecord_customer_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicemanagementrecord',
            name='service_start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='servicemanagementrecord',
            name='service_end_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
