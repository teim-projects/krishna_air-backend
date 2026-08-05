# Generated migration to add parent_document_type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_rolepermission_modify_all_permission_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='rolepermission',
            name='parent_document_type',
            field=models.CharField(blank=True, help_text="Parent module for hierarchy (e.g., 'PO' has parent 'Inventory')", max_length=100, null=True),
        ),
    ]
