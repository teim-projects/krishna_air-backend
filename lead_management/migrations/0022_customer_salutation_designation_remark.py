from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lead_management', '0021_sync_lead_qualifying_questions'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='salutation',
            field=models.CharField(
                blank=True,
                choices=[('Mr.', 'Mr.'), ('Mrs.', 'Mrs.')],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='customer',
            name='designation',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='remark',
            field=models.TextField(blank=True, null=True),
        ),
    ]
