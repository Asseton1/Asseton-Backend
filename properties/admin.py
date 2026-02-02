from django.contrib import admin
from .models import Feature, PropertyType, Property, PropertyImage, State, District, City

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'created_at', 'updated_at')
    list_filter = ('state',)
    search_fields = ('name',)

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'created_at', 'updated_at')
    list_filter = ('district__state', 'district')
    search_fields = ('name',)

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'property_for', 'state', 'district', 'city', 'property_type', 'price', 'created_at')
    list_filter = ('property_for', 'state', 'district', 'city', 'property_type', 'bedrooms', 'bathrooms', 'furnishing')
    search_fields = ('title', 'description', 'address')
    inlines = [PropertyImageInline]
    filter_horizontal = ('features',)
