# Generated by Django 4.2.11 on 2024-05-22 14:19

from django.db import migrations, models

from registrations.models import VAT_CODE_MAPPING


def migrate_vat_code(apps, schema_editor):
    account_model = apps.get_model("registrations", "WebStoreAccount")
    product_mapping_model = apps.get_model(
        "registrations", "RegistrationWebStoreProductMapping"
    )

    for web_store_account in account_model.objects.filter(
        vat_code__in=VAT_CODE_MAPPING.values()
    ).only("pk", "vat_code"):
        product_mapping_model.objects.filter(account_id=web_store_account.pk).update(
            vat_code=web_store_account.vat_code
        )


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0048_webstoreaccount_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="registrationwebstoreproductmapping",
            name="vat_code",
            field=models.CharField(
                default="44",
                max_length=2,
                choices=[
                    ("47", "25.5 %"),
                    ("44", "24 %"),
                    ("45", "14 %"),
                    ("46", "10 %"),
                    ("4U", "0 %"),
                ],
            ),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_vat_code, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="webstoreaccount",
            name="vat_code",
        ),
    ]
