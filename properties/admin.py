from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Feature, PropertyType, Property, PropertyImage, State, District, City, SiteSettings

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

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for SiteSettings (singleton pattern).
    Only allows editing the single instance (pk=1).
    """
    list_display = ('filter_radius', 'created_at', 'updated_at')
    fields = ('filter_radius', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        """Prevent adding new instances - only one should exist"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting the singleton instance"""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """
        Redirect to the edit page of the singleton instance.
        """
        obj = SiteSettings.get_settings()
        return HttpResponseRedirect(
            reverse('admin:properties_sitesettings_change', args=[obj.pk])
        )
