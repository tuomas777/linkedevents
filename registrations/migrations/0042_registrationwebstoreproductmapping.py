# Generated by Django 4.2.11 on 2024-03-26 14:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("registrations", "0041_webstoreaccount"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistrationWebStoreProductMapping",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("external_product_id", models.CharField(max_length=64)),
                (
                    "account",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="web_store_product_mapping",
                        to="registrations.webstoreaccount",
                    ),
                ),
                (
                    "merchant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="web_store_product_mapping",
                        to="registrations.webstoremerchant",
                    ),
                ),
                (
                    "registration",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="web_store_product_mapping",
                        to="registrations.registration",
                    ),
                ),
            ],
        ),
    ]
