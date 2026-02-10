from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FeatureViewSet, PropertyTypeViewSet, PropertyViewSet,
    StateViewSet, DistrictViewSet, CityViewSet,
    HeroBannerViewSet, OfferBannerViewSet, ContactViewSet,
    SiteSettingsViewSet
)

router = DefaultRouter()
router.register(r'states', StateViewSet)
router.register(r'districts', DistrictViewSet)
router.register(r'cities', CityViewSet)
router.register(r'features', FeatureViewSet)
router.register(r'property-types', PropertyTypeViewSet)
router.register(r'properties', PropertyViewSet)
router.register(r'hero-banners', HeroBannerViewSet)
router.register(r'offer-banners', OfferBannerViewSet)
router.register(r'contacts', ContactViewSet)
router.register(r'site-settings', SiteSettingsViewSet, basename='site-settings')

urlpatterns = [
    path('', include(router.urls)),
]

