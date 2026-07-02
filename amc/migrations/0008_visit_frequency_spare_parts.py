from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoice', '0012_invoice_delivery_chalan_date'),
        ('inventory', '0020_deliverychallan_deliverychallanitem'),
        ('amc', '0007_amc_type_and_service_customer'),
    ]

    operations = [
        migrations.AddField(
            model_name='amccontract',
            name='visit_frequency',
            field=models.CharField(
                choices=[
                    ('MONTHLY', 'Monthly'),
                    ('QUARTERLY', 'Quarterly'),
                    ('HALF_YEARLY', 'Half Yearly'),
                    ('YEARLY', 'Yearly'),
                ],
                default='QUARTERLY',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='AMCSparePart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_used', models.DecimalField(decimal_places=2, max_digits=10)),
                ('unit', models.CharField(default='Nos', max_length=20)),
                ('rate_per_unit', models.DecimalField(decimal_places=2, max_digits=10)),
                ('gst_percent', models.DecimalField(decimal_places=2, default=18, max_digits=5)),
                ('hsn_sac', models.CharField(blank=True, max_length=50, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('total_cost', models.DecimalField(decimal_places=2, editable=False, max_digits=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('amc_contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spare_parts', to='amc.amccontract')),
                ('inventory_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='amc_spare_parts', to='inventory.inventoryitem')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='amc_spare_parts', to='invoice.invoice')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
