from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Property, SiteSettings
from .utils import invalidate_locations_cache


@receiver(post_save, sender=Property)
@receiver(post_delete, sender=Property)
def clear_locations_cache_on_property_change(sender, **kwargs):
    invalidate_locations_cache()


@receiver(post_save, sender=SiteSettings)
def clear_locations_cache_on_settings_change(sender, **kwargs):
    # filter_radius affects clustering; refresh cached location groups.
    invalidate_locations_cache()
