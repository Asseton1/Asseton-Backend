# Generated migration to change price field from DecimalField to TextField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0011_all_property_changes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='property',
            name='price',
            field=models.TextField(help_text="Price can be numeric (e.g., '2500000') or text (e.g., '25 Lakh', 'Negotiable', 'Contact for price')"),
        ),
    ]

