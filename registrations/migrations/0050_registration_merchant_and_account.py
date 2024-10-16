# Generated by Django 4.2.11 on 2024-05-24 14:32

import django.db.models.deletion
from django.db import migrations, models


def migrate_merchant_and_account_data(apps, schema_editor):
    product_mapping_model = apps.get_model(
        "registrations", "RegistrationWebStoreProductMapping"
    )
    web_store_merchant_model = apps.get_model("registrations", "WebStoreMerchant")
    registration_merchant_model = apps.get_model(
        "registrations", "RegistrationWebStoreMerchant"
    )
    registration_account_model = apps.get_model(
        "registrations", "RegistrationWebStoreAccount"
    )

    registration_merchants = []
    registration_accounts = []

    for product_mapping in product_mapping_model.objects.all():
        if merchant := web_store_merchant_model.objects.filter(
            merchant_id=product_mapping.external_merchant_id
        ).first():
            registration_merchants.append(
                registration_merchant_model(
                    registration=product_mapping.registration,
                    merchant=merchant,
                    external_merchant_id=product_mapping.external_merchant_id,
                )
            )

        registration_accounts.append(
            registration_account_model(
                registration=product_mapping.registration,
                account=product_mapping.account,
                name=product_mapping.account.name,
                company_code=product_mapping.account.company_code,
                main_ledger_account=product_mapping.account.main_ledger_account,
                balance_profit_center=product_mapping.account.balance_profit_center,
                internal_order=product_mapping.account.internal_order,
                profit_center=product_mapping.account.profit_center,
                project=product_mapping.account.project,
                operation_area=product_mapping.account.operation_area,
            )
        )

    registration_merchant_model.objects.bulk_create(registration_merchants)
    registration_account_model.objects.bulk_create(registration_accounts)


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0049_remove_webstoreaccount_vat_code_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistrationWebStoreMerchant",
            fields=[
                (
                    "registration",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registration_merchant",
                        primary_key=True,
                        serialize=False,
                        to="registrations.registration",
                    ),
                ),
                ("external_merchant_id", models.CharField(max_length=64)),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registration_merchants",
                        to="registrations.webstoremerchant",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RegistrationWebStoreAccount",
            fields=[
                (
                    "name",
                    models.CharField(max_length=255, verbose_name="Name"),
                ),
                (
                    "company_code",
                    models.CharField(max_length=4, verbose_name="SAP company code"),
                ),
                (
                    "main_ledger_account",
                    models.CharField(max_length=6, verbose_name="Main ledger account"),
                ),
                (
                    "balance_profit_center",
                    models.CharField(
                        max_length=10, verbose_name="Balance profit center"
                    ),
                ),
                (
                    "internal_order",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=10,
                        verbose_name="Internal order",
                    ),
                ),
                (
                    "profit_center",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=7,
                        verbose_name="Profit center",
                    ),
                ),
                (
                    "project",
                    models.CharField(
                        blank=True, default="", max_length=16, verbose_name="Project"
                    ),
                ),
                (
                    "operation_area",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=6,
                        verbose_name="SAP functional area",
                    ),
                ),
                (
                    "registration",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registration_account",
                        primary_key=True,
                        serialize=False,
                        to="registrations.registration",
                    ),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registration_accounts",
                        to="registrations.webstoreaccount",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.RunPython(
            migrate_merchant_and_account_data, migrations.RunPython.noop
        ),
        migrations.RemoveField(
            model_name="registrationwebstoreproductmapping",
            name="account",
        ),
        migrations.RemoveField(
            model_name="registrationwebstoreproductmapping",
            name="external_merchant_id",
        ),
    ]
