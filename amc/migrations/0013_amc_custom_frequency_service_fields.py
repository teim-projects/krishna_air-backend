from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('amc', '0012_alter_amccontract_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='amccontract',
            name='schedule_note',
            field=models.TextField(blank=True, help_text='Custom visit plan notes (e.g. all visits within first 6 months).', null=True),
        ),
        migrations.AddField(
            model_name='amccontract',
            name='total_visit_count',
            field=models.PositiveIntegerField(blank=True, help_text='Required when visit_frequency is CUSTOM (e.g. 4 visits in 6 months).', null=True),
        ),
        migrations.AddField(
            model_name='servicemanagementrecord',
            name='service_frequency_count',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='servicemanagementrecord',
            name='warranty_period_months',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='amccontract',
            name='visit_frequency',
            field=models.CharField(
                choices=[
                    ('MONTHLY', 'Monthly'),
                    ('QUARTERLY', 'Quarterly'),
                    ('HALF_YEARLY', 'Half Yearly'),
                    ('YEARLY', 'Yearly'),
                    ('CUSTOM', 'Custom'),
                ],
                default='QUARTERLY',
                max_length=20,
            ),
        ),
    ]
