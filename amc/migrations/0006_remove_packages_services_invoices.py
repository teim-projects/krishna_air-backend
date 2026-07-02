from django.db import migrations, models


def copy_package_names(apps, schema_editor):
    AMCContract = apps.get_model('amc', 'AMCContract')
    AMCPackage = apps.get_model('amc', 'AMCPackage')
    for contract in AMCContract.objects.exclude(package_id=None):
        try:
            pkg = AMCPackage.objects.get(pk=contract.package_id)
            contract.package_name = pkg.name
            contract.save(update_fields=['package_name'])
        except AMCPackage.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('amc', '0005_servicemanagementrecord_service_dates'),
    ]

    operations = [
        migrations.AddField(
            model_name='amccontract',
            name='package_name',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.RunPython(copy_package_names, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='AMCInvoice',
        ),
        migrations.DeleteModel(
            name='AMCServiceLabor',
        ),
        migrations.DeleteModel(
            name='AMCServiceParts',
        ),
        migrations.DeleteModel(
            name='AMCService',
        ),
        migrations.RemoveField(
            model_name='amccontract',
            name='package',
        ),
        migrations.DeleteModel(
            name='AMCPackage',
        ),
    ]
