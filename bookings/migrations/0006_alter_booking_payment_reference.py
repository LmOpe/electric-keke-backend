# Generated by Django 5.1 on 2024-11-06 02:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0005_alter_booking_payment_reference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='payment_reference',
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
    ]