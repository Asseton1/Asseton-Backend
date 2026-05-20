from django.db import migrations, models


def approve_existing_pending(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    Property.objects.filter(moderation_status='pending').update(moderation_status='approved')


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0014_property_is_featured'),
    ]

    operations = [
        migrations.AlterField(
            model_name='property',
            name='moderation_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                ],
                db_index=True,
                default='approved',
                max_length=20,
            ),
        ),
        migrations.RunPython(approve_existing_pending, migrations.RunPython.noop),
    ]
