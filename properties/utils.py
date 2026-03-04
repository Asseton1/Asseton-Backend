"""
Utility functions for the properties app.
"""
import math
from decimal import Decimal


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
