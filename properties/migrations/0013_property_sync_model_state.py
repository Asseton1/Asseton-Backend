from django.db import migrations, models


def backfill_null_property_fields(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    Property.objects.filter(bathrooms__isnull=True).update(bathrooms=1)
    Property.objects.filter(bedrooms__isnull=True).update(bedrooms=1)
    Property.objects.filter(built_year__isnull=True).update(built_year=2000)
    Property.objects.filter(parking_spaces__isnull=True).update(parking_spaces=0)
    Property.objects.filter(furnishing__isnull=True).update(furnishing='Unfurnished')
    Property.objects.filter(email__isnull=True).update(email='unknown@asseton.local')
    Property.objects.filter(email='').update(email='unknown@asseton.local')


def ensure_sitesettings_table(apps, schema_editor):
    table = 'properties_sitesettings'
    if table in schema_editor.connection.introspection.table_names():
        return

    class SiteSettings(models.Model):
        filter_radius = models.DecimalField(max_digits=10, decimal_places=2, default=10.0)
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)

        class Meta:
            app_label = 'properties'
            db_table = table

    schema_editor.create_model(SiteSettings)


def seed_sitesettings(apps, schema_editor):
    SiteSettings = apps.get_model('properties', 'SiteSettings')
    SiteSettings.objects.get_or_create(pk=1, defaults={'filter_radius': 10.0})


def ensure_area_unit_column(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    table = Property._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
        column_names = {col.name for col in description}

    if 'area_unit' in column_names:
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE `{table}` SET `area_unit` = %s "
                f"WHERE `area_unit` IS NULL OR `area_unit` = %s",
                ['sqft', ''],
            )
        return

    field = models.CharField(
        max_length=10,
        choices=[('sqft', 'Square Feet'), ('cent', 'Cent')],
        default='sqft',
        help_text='Unit of measurement for area',
    )
    field.set_attributes_from_name('area_unit')
    schema_editor.add_field(Property, field)


def remove_area_unit_column(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')
    table = Property._meta.db_table
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
        column_names = {col.name for col in description}

    if 'area_unit' in column_names:
        field = models.CharField(max_length=10, default='sqft')
        field.set_attributes_from_name('area_unit')
        schema_editor.remove_field(Property, field)


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0012_property_moderation_status'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='SiteSettings',
                    fields=[
                        (
                            'id',
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name='ID',
                            ),
                        ),
                        (
                            'filter_radius',
                            models.DecimalField(
                                decimal_places=2,
                                default=10.0,
                                help_text='Default filter radius in kilometers for latitude/longitude-based property searches',
                                max_digits=10,
                            ),
                        ),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        'verbose_name': 'Site Settings',
                        'verbose_name_plural': 'Site Settings',
                    },
                ),
            ],
            database_operations=[
                migrations.RunPython(ensure_sitesettings_table, migrations.RunPython.noop),
            ],
        ),
        migrations.RunPython(seed_sitesettings, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='property',
                    name='area_unit',
                    field=models.CharField(
                        choices=[('sqft', 'Square Feet'), ('cent', 'Cent')],
                        default='sqft',
                        help_text='Unit of measurement for area',
                        max_length=10,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(ensure_area_unit_column, remove_area_unit_column),
            ],
        ),
        migrations.RunPython(backfill_null_property_fields, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='property',
            name='area',
            field=models.PositiveIntegerField(help_text='Area value'),
        ),
        migrations.AlterField(
            model_name='property',
            name='bathrooms',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='property',
            name='bedrooms',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='property',
            name='built_year',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='property',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='property',
            name='furnishing',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='property',
            name='parking_spaces',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='property',
            name='price',
            field=models.TextField(
                help_text="Price can be numeric (e.g., '2500000') or text (e.g., '25 Lakh', 'Negotiable', 'Contact for price')"
            ),
        ),
    ]
