from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('amc', '0013_amc_custom_frequency_service_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='AMCServiceVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visit_number', models.PositiveIntegerField()),
                ('planned_date', models.DateField()),
                ('status', models.CharField(
                    choices=[
                        ('SCHEDULED', 'Scheduled'),
                        ('ASSIGNED', 'Assigned'),
                        ('COMPLETED', 'Completed'),
                        ('CANCELLED', 'Cancelled'),
                    ],
                    default='SCHEDULED',
                    max_length=20,
                )),
                ('work_description', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amc_contract', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='service_visits',
                    to='amc.amccontract',
                )),
                ('service_record', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='amc_service_visits',
                    to='amc.servicemanagementrecord',
                )),
                ('technician_work_record', models.OneToOneField(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='amc_service_visit',
                    to='amc.technicianworkrecord',
                )),
            ],
            options={
                'ordering': ['visit_number'],
            },
        ),
        migrations.AddConstraint(
            model_name='amcservicevisit',
            constraint=models.UniqueConstraint(
                fields=('amc_contract', 'visit_number'),
                name='uniq_amc_contract_visit_number',
            ),
        ),
    ]
