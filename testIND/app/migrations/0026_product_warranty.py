# Generated by Django 4.2.3 on 2025-02-14 07:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0025_delete_stockproduct_stockproduct'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='warranty',
            field=models.CharField(choices=[('1 Year', '1 Year'), ('2 Year', '2 Year'), ('3 Year', '3 Year')], default='1 Year', max_length=20),
        ),
    ]
