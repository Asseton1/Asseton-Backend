# Generated manually for listing performance

from decimal import Decimal, InvalidOperation

from django.db import migrations, models


def backfill_price_numeric(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    qs = Property.objects.all().only('id', 'price')
    batch = []
    for p in qs.iterator(chunk_size=500):
        raw = (p.price or "").strip()
        try:
            pn = Decimal(raw)
        except (InvalidOperation, TypeError, ValueError):
            pn = None
        p.price_numeric = pn
        batch.append(p)
        if len(batch) >= 500:
            Property.objects.bulk_update(batch, ['price_numeric'])
            batch.clear()
    if batch:
        Property.objects.bulk_update(batch, ['price_numeric'])


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0014_property_area_unit_alter_property_area_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='price_numeric',
            field=models.DecimalField(
                blank=True,
                db_index=True,
                decimal_places=2,
                help_text='Parsed from price when it is a plain decimal string; used for fast range filters.',
                max_digits=20,
                null=True,
            ),
        ),
        migrations.RunPython(backfill_price_numeric, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name='property',
            index=models.Index(fields=['created_at'], name='property_created_at_idx'),
        ),
    ]
