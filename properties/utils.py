"""
Utility functions for the properties app.
"""
import math

from django.core.cache import cache


LOCATIONS_CACHE_VERSION_KEY = "property_locations_cache_version"
LOCATIONS_CACHE_TTL = 60


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Return the great-circle distance in kilometers between two points
    given by (lat1, lon1) and (lat2, lon2) using the Haversine formula.
    Accepts Decimal or float.
    """
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)
    R = 6371  # Earth's radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_locations_cache_version():
    """Return the current locations cache generation (bumped on invalidation)."""
    version = cache.get(LOCATIONS_CACHE_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(LOCATIONS_CACHE_VERSION_KEY, version, timeout=None)
    return version


def locations_cache_key(include_unapproved, property_for, search, filter_radius_km):
    """Stable cache key for a clustered locations result set (before pagination)."""
    version = get_locations_cache_version()
    scope = "all" if include_unapproved else "approved"
    prop_for = property_for or ""
    search_term = (search or "").strip().lower()
    radius = f"{float(filter_radius_km):.2f}"
    return f"property_locations:v{version}:{scope}:{prop_for}:{search_term}:{radius}"


def invalidate_locations_cache():
    """
    Invalidate all locations caches by bumping the version key.
    LocMemCache does not support delete_pattern; versioning is reliable.
    """
    try:
        cache.incr(LOCATIONS_CACHE_VERSION_KEY)
    except ValueError:
        cache.set(LOCATIONS_CACHE_VERSION_KEY, 1, timeout=None)
