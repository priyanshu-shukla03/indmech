# Generated by Django 5.1.5 on 2025-02-04 06:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0016_order_docker_number'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='docker_number',
            new_name='docket_number',
        ),
        migrations.AddField(
            model_name='order',
            name='freight',
            field=models.FloatField(default=150),
            preserve_default=False,
        ),
    ]
