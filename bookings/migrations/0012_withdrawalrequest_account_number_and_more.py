# Generated by Django 5.1 on 2024-11-09 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0011_alter_withdrawalrequest_reference'),
    ]

    operations = [
        migrations.AddField(
            model_name='withdrawalrequest',
            name='account_number',
            field=models.CharField(default=2387387233, max_length=12),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='withdrawalrequest',
            name='bank_code',
            field=models.CharField(default='057', max_length=5),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='withdrawalrequest',
            name='currency',
            field=models.CharField(default='NGN', max_length=5),
            preserve_default=False,
        ),
    ]