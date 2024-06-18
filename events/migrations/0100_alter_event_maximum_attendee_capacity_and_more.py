# Generated by Django 4.2.13 on 2024-06-10 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0099_offer_price_groups"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="maximum_attendee_capacity",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="maximum attendee capacity"
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="minimum_attendee_capacity",
            field=models.PositiveIntegerField(
                blank=True, null=True, verbose_name="minimum attendee capacity"
            ),
        ),
    ]