# Generated by Django 4.2.11 on 2024-04-17 12:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0042_registrationwebstoreproductmapping"),
    ]

    operations = [
        migrations.AlterField(
            model_name="registrationwebstoreproductmapping",
            name="account",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="web_store_product_mappings",
                to="registrations.webstoreaccount",
            ),
        ),
        migrations.AlterField(
            model_name="registrationwebstoreproductmapping",
            name="merchant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="web_store_product_mappings",
                to="registrations.webstoremerchant",
            ),
        ),
    ]
