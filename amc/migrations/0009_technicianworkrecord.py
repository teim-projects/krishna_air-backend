from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
        ('amc', '0008_visit_frequency_spare_parts'),
    ]

    operations = [
        migrations.CreateModel(
            name='TechnicianWorkRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(max_length=255)),
                ('customer_phone', models.CharField(max_length=15)),
                ('customer_address', models.TextField()),
                ('payment_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('gps_location', models.CharField(blank=True, default='', max_length=255)),
                ('work_description', models.TextField(blank=True, default='')),
                ('work_date', models.DateField(default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_technician_work_records', to='api.customuser')),
                ('service_record', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='technician_work_records', to='amc.servicemanagementrecord')),
                ('technician', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='technician_work_records', to='api.customuser')),
            ],
            options={
                'ordering': ['-work_date', '-created_at'],
            },
        ),
    ]
