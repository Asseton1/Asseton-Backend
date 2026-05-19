from django.db import migrations, models


def ensure_moderation_status_column(apps, schema_editor):
    """
    Add moderation_status when missing (local DB). On Azure the column may already exist
    from a manual migration — then only backfill empty values.
    """
    Property = apps.get_model('properties', 'Property')
    table = Property._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
        column_names = {col.name for col in description}

    field = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending',
        db_index=True,
    )
    field.set_attributes_from_name('moderation_status')

    if 'moderation_status' not in column_names:
        schema_editor.add_field(Property, field)
        # Existing listings were already public; keep them visible after this change.
        Property.objects.all().update(moderation_status='approved')
        return

    Property.objects.filter(moderation_status__isnull=True).update(moderation_status='approved')
    Property.objects.filter(moderation_status='').update(moderation_status='approved')


def remove_moderation_status_column(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    table = Property._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
        column_names = {col.name for col in description}

    if 'moderation_status' in column_names:
        field = models.CharField(max_length=20, default='pending')
        field.set_attributes_from_name('moderation_status')
        schema_editor.remove_field(Property, field)


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0011_all_property_changes'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='property',
                    name='moderation_status',
                    field=models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('approved', 'Approved'),
                            ('rejected', 'Rejected'),
                        ],
                        db_index=True,
                        default='pending',
                        max_length=20,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    ensure_moderation_status_column,
                    remove_moderation_status_column,
                ),
            ],
        ),
    ]
