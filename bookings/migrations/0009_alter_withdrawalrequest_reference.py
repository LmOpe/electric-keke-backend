# Generated by Django 5.1 on 2024-11-09 14:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0008_withdrawalrequest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='withdrawalrequest',
            name='reference',
            field=models.CharField(max_length=100),
        ),
    ]
