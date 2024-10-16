# Generated by Django 1.9.11 on 2017-03-15 15:54

import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0036_add_n_events_to_place"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="place",
            managers=[
                ("geo_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddField(
            model_name="keyword",
            name="n_events_changed",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="place",
            name="n_events_changed",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
