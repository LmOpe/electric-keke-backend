# Generated by Django 5.1 on 2024-11-06 01:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_alter_booking_payment_reference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='payment_reference',
            field=models.UUIDField(blank=True, null=True, unique=True),
        ),
    ]