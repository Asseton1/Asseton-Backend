from django.db import migrations, models


def ensure_is_featured_column(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    table = Property._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
        column_names = {col.name for col in description}

    field = models.BooleanField(default=False, db_index=True)
    field.set_attributes_from_name('is_featured')

    if 'is_featured' not in column_names:
        schema_editor.add_field(Property, field)
        return

    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE `{table}` SET `is_featured` = %s WHERE `is_featured` IS NULL",
            [False],
        )


def remove_is_featured_column(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    table = Property._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
        column_names = {col.name for col in description}

    if 'is_featured' in column_names:
        field = models.BooleanField(default=False)
        field.set_attributes_from_name('is_featured')
        schema_editor.remove_field(Property, field)


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0013_property_sync_model_state'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='property',
                    name='is_featured',
                    field=models.BooleanField(db_index=True, default=False),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    ensure_is_featured_column,
                    remove_is_featured_column,
                ),
            ],
        ),
    ]
