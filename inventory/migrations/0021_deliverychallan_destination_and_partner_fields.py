import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_customuser_staff_profile_fields'),
        ('inventory', '0020_deliverychallan_deliverychallanitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='deliverychallan',
            name='destination_type',
            field=models.CharField(
                blank=True,
                choices=[('branch', 'Branch'), ('site', 'Site')],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='deliverychallan',
            name='branch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='delivery_challans',
                to='api.branchmanagement',
            ),
        ),
        migrations.AddField(
            model_name='deliverychallan',
            name='site',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='delivery_challans',
                to='api.sitemanagement',
            ),
        ),
        migrations.AddField(
            model_name='deliverychallan',
            name='delivery_partner_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='deliverychallan',
            name='delivery_person_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='deliverychallan',
            name='delivery_person_phone',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='deliverychallan',
            name='delivery_remark',
            field=models.TextField(blank=True, null=True),
        ),
    ]
