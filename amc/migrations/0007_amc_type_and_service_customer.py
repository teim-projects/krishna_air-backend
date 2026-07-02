from django.db import migrations, models
import django.db.models.deletion


def migrate_package_name_to_amc_type(apps, schema_editor):
    AMCContract = apps.get_model('amc', 'AMCContract')
    for contract in AMCContract.objects.all():
        name = (contract.package_name or '').lower()
        if 'non' in name and 'comprehensive' in name:
            contract.amc_type = 'NON_COMPREHENSIVE'
        else:
            contract.amc_type = 'COMPREHENSIVE'
        contract.save(update_fields=['amc_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('amc', '0006_remove_packages_services_invoices'),
        ('lead_management', '0019_add_qualifying_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicemanagementrecord',
            name='customer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='service_management_records',
                to='lead_management.customer',
            ),
        ),
        migrations.AddField(
            model_name='servicemanagementrecord',
            name='amc_service_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('COMPREHENSIVE', 'Comprehensive'),
                    ('NON_COMPREHENSIVE', 'Non-Comprehensive'),
                ],
                default='',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='amccontract',
            name='amc_type',
            field=models.CharField(
                choices=[
                    ('COMPREHENSIVE', 'Comprehensive'),
                    ('NON_COMPREHENSIVE', 'Non-Comprehensive'),
                ],
                default='COMPREHENSIVE',
                max_length=20,
            ),
        ),
        migrations.RunPython(migrate_package_name_to_amc_type, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='amccontract',
            name='package_name',
        ),
    ]
