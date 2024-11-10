# Generated by Django 5.1 on 2024-11-09 09:42

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0007_booking_paid_alter_booking_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WithdrawalRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completed', models.BooleanField(default=False)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('reference', models.CharField(max_length=50)),
                ('rider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rider_withdrawal_requests', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
