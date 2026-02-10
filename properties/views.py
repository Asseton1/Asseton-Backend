from datetime import datetime, time
from decimal import Decimal, InvalidOperation
import math

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, permissions, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Feature,
    PropertyType,
    Property,
    PropertyImage,
    State,
    District,
    City,
    HeroBanner,
    OfferBanner,
    Contact,
    SiteSettings,
)
from .pagination import PropertyPagination
from .serializers import (
    FeatureSerializer,
    PropertyTypeSerializer,
    PropertySerializer,
    PropertyImageSerializer,
    StateSerializer,
    DistrictSerializer,
    CitySerializer,
    HeroBannerSerializer,
    OfferBannerSerializer,
    ContactSerializer,
    SiteSettingsSerializer,
)

class StateViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows states to be viewed or edited.
    GET methods (list and retrieve) are publicly accessible.
    Other methods require authentication.
    """
    queryset = State.objects.all()
    serializer_class = StateSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

class DistrictViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows districts to be viewed or edited.
    """
    queryset = District.objects.all()
    serializer_class = DistrictSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = District.objects.all()
        state_id = self.request.query_params.get('state_id')
        if state_id:
            queryset = queryset.filter(state_id=state_id)
        return queryset

class CityViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows cities to be viewed or edited.
    """
    queryset = City.objects.all()
    serializer_class = CitySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = City.objects.all()
        district_id = self.request.query_params.get('district_id')
        if district_id:
            queryset = queryset.filter(district_id=district_id)
        return queryset

class FeatureViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows features to be viewed or edited.
    GET methods (list and retrieve) are publicly accessible.
    Other methods require authentication.
    """
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def update(self, request, *args, **kwargs):
        # Override to prevent PUT method
        return Response({"detail": "Method 'PUT' not allowed."}, status=405)
    
    def partial_update(self, request, *args, **kwargs):
        # Use PATCH for updates
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class PropertyTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows property types to be viewed or edited.
    GET methods (list and retrieve) are publicly accessible.
    Other methods require authentication.
    """
    queryset = PropertyType.objects.all()
    serializer_class = PropertyTypeSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def update(self, request, *args, **kwargs):
        # Override to prevent PUT method
        return Response({"detail": "Method 'PUT' not allowed."}, status=405)
    
    def partial_update(self, request, *args, **kwargs):
        # Use PATCH for updates
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class PropertyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows properties to be viewed or edited.
    GET methods (list and retrieve) are publicly accessible.
    Other methods require authentication.
    """
    queryset = Property.objects.all().select_related('state', 'district', 'city', 'property_type')
    serializer_class = PropertySerializer
    pagination_class = PropertyPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        price_min = params.get('price_min')
        price_max = params.get('price_max')
        property_for = params.get('property_for')
        ownership = params.get('ownership')
        area_min = params.get('area_min')
        area_max = params.get('area_max')
        area_unit = params.get('area_unit', 'sqft').lower()
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        property_type = params.get('property_type')
        bedrooms_min = params.get('bedrooms_min')
        bedrooms_max = params.get('bedrooms_max')
        bathrooms_min = params.get('bathrooms_min')
        bathrooms_max = params.get('bathrooms_max')
        state_id = params.get('state_id')
        district_id = params.get('district_id')
        city_id = params.get('city_id')
        location = params.get('location')
        furnishing = params.get('furnishing')
        search = params.get('search')
        
        # Latitude/Longitude filtering parameters
        latitude = params.get('latitude')
        longitude = params.get('longitude')
        radius = params.get('radius')  # in kilometers
        lat_min = params.get('lat_min')
        lat_max = params.get('lat_max')
        lng_min = params.get('lng_min')
        lng_max = params.get('lng_max')

        def convert_decimal(value):
            try:
                return Decimal(value)
            except (InvalidOperation, TypeError):
                return None

        def convert_int(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        # Price filtering disabled - price is now TextField and supports text values like "25 Lakh", "Negotiable", etc.
        # Numeric comparison filters (price_min, price_max) are not available with text-based price field
        # If needed, price filtering can be implemented using text search or custom parsing logic
        # price_min_decimal = convert_decimal(price_min)
        # if price_min_decimal is not None:
        #     queryset = queryset.filter(price__gte=price_min_decimal)
        #
        # price_max_decimal = convert_decimal(price_max)
        # if price_max_decimal is not None:
        #     queryset = queryset.filter(price__lte=price_max_decimal)

        if property_for in dict(Property.PROPERTY_FOR_CHOICES):
            queryset = queryset.filter(property_for=property_for)

        if ownership in dict(Property.OWNERSHIP_CHOICES):
            queryset = queryset.filter(property_ownership=ownership)

        if furnishing:
            queryset = queryset.filter(furnishing__iexact=furnishing)

        # Area filtering - filter by matching area_unit and area value (no conversion)
        if area_unit in dict(Property.AREA_UNIT_CHOICES):
            queryset = queryset.filter(area_unit=area_unit)
            
            area_min_value = convert_int(area_min)
            if area_min_value is not None:
                queryset = queryset.filter(area__gte=area_min_value)

            area_max_value = convert_int(area_max)
            if area_max_value is not None:
                queryset = queryset.filter(area__lte=area_max_value)

        if date_from:
            parsed_date = parse_date(date_from)
            if parsed_date:
                start_datetime = timezone.make_aware(datetime.combine(parsed_date, time.min))
                queryset = queryset.filter(created_at__gte=start_datetime)

        if date_to:
            parsed_date = parse_date(date_to)
            if parsed_date:
                end_datetime = timezone.make_aware(datetime.combine(parsed_date, time.max))
                queryset = queryset.filter(created_at__lte=end_datetime)

        property_type_id = convert_int(property_type)
        if property_type_id is not None:
            queryset = queryset.filter(property_type_id=property_type_id)

        bedrooms_min_value = convert_int(bedrooms_min)
        if bedrooms_min_value is not None:
            queryset = queryset.filter(bedrooms__gte=bedrooms_min_value)

        bedrooms_max_value = convert_int(bedrooms_max)
        if bedrooms_max_value is not None:
            queryset = queryset.filter(bedrooms__lte=bedrooms_max_value)

        bathrooms_min_value = convert_int(bathrooms_min)
        if bathrooms_min_value is not None:
            queryset = queryset.filter(bathrooms__gte=bathrooms_min_value)

        bathrooms_max_value = convert_int(bathrooms_max)
        if bathrooms_max_value is not None:
            queryset = queryset.filter(bathrooms__lte=bathrooms_max_value)

        state_value = convert_int(state_id)
        if state_value is not None:
            queryset = queryset.filter(state_id=state_value)

        district_value = convert_int(district_id)
        if district_value is not None:
            queryset = queryset.filter(district_id=district_value)

        city_value = convert_int(city_id)
        if city_value is not None:
            queryset = queryset.filter(city_id=city_value)

        if location:
            queryset = queryset.filter(
                Q(city__name__icontains=location)
                | Q(district__name__icontains=location)
                | Q(state__name__icontains=location)
            )

        if search:
            search_terms = [term.strip() for term in search.split() if term.strip()]
            if search_terms:
                combined_query = Q()
                for term in search_terms:
                    term_query = (
                        Q(title__icontains=term)
                        | Q(description__icontains=term)
                        | Q(property_type__name__icontains=term)
                        | Q(contact_name__icontains=term)
                        | Q(features__name__icontains=term)
                        | Q(nearby_places__icontains=term)
                        | Q(state__name__icontains=term)
                        | Q(district__name__icontains=term)
                        | Q(city__name__icontains=term)
                        | Q(property_for__icontains=term)
                        | Q(property_ownership__icontains=term)
                        | Q(furnishing__icontains=term)
                        | Q(price__icontains=term)
                    )
                    combined_query &= term_query if combined_query else term_query
                queryset = queryset.filter(combined_query)

        # Latitude/Longitude filtering
        lat_min_value = convert_decimal(lat_min)
        lat_max_value = convert_decimal(lat_max)
        lng_min_value = convert_decimal(lng_min)
        lng_max_value = convert_decimal(lng_max)
        lat_value = convert_decimal(latitude)
        lng_value = convert_decimal(longitude)
        radius_value = convert_decimal(radius)
        
        # Check if any lat/lng filtering is being applied
        has_lat_lng_filter = any([
            lat_min_value is not None,
            lat_max_value is not None,
            lng_min_value is not None,
            lng_max_value is not None,
            (lat_value is not None and lng_value is not None)
        ])
        
        # Only filter by coordinates if lat/lng filters are being used
        if has_lat_lng_filter:
            # Ensure we only filter properties that have coordinates
            queryset = queryset.filter(latitude__isnull=False, longitude__isnull=False)
            
            # Bounding box filtering
            if lat_min_value is not None:
                queryset = queryset.filter(latitude__gte=lat_min_value)
            if lat_max_value is not None:
                queryset = queryset.filter(latitude__lte=lat_max_value)
            if lng_min_value is not None:
                queryset = queryset.filter(longitude__gte=lng_min_value)
            if lng_max_value is not None:
                queryset = queryset.filter(longitude__lte=lng_max_value)
            
            # Distance-based filtering (using bounding box approximation for efficiency)
            # This finds properties within a radius (in km) from a given point
            if lat_value is not None and lng_value is not None:
                # Determine which radius to use: query parameter or admin-defined default
                if radius_value is not None:
                    # Use the radius from query parameter (override admin setting)
                    radius_to_use = radius_value
                else:
                    # Use the admin-defined filter_radius from SiteSettings
                    site_settings = SiteSettings.get_settings()
                    radius_to_use = Decimal(str(site_settings.filter_radius))
                
                # Convert radius from km to degrees (approximate)
                # 1 degree latitude ≈ 111 km
                # 1 degree longitude ≈ 111 km * cos(latitude)
                lat_degree = radius_to_use / Decimal('111.0')
                lng_degree = radius_to_use / (Decimal('111.0') * Decimal(str(abs(math.cos(math.radians(float(lat_value)))))))
                
                # Create bounding box
                queryset = queryset.filter(
                    latitude__gte=lat_value - lat_degree,
                    latitude__lte=lat_value + lat_degree,
                    longitude__gte=lng_value - lng_degree,
                    longitude__lte=lng_value + lng_degree
                )

        return queryset.order_by('-created_at').distinct()

    @action(detail=True, methods=['delete'])
    def delete_image(self, request, pk=None):
        """
        Delete a specific image from a property
        """
        property = self.get_object()
        try:
            image_id = request.data.get('image_id')
            image = PropertyImage.objects.get(id=image_id, property=property)
            image.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PropertyImage.DoesNotExist:
            return Response(
                {"detail": "Image not found or does not belong to this property."},
                status=status.HTTP_404_NOT_FOUND
            )

class HeroBannerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows hero banners to be viewed or edited.
    GET methods (list and retrieve) are publicly accessible.
    Other methods require authentication.
    """
    queryset = HeroBanner.objects.all().order_by('-created_at')
    serializer_class = HeroBannerSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        # Delete all existing banners before creating new one
        HeroBanner.objects.all().delete()
        return super().create(request, *args, **kwargs)

class OfferBannerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows offer banners to be viewed or edited.
    GET methods (list and retrieve) are publicly accessible.
    Other methods require authentication.
    """
    queryset = OfferBanner.objects.all().order_by('-created_at')
    serializer_class = OfferBannerSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        # Delete all existing banners before creating new one
        OfferBanner.objects.all().delete()
        return super().create(request, *args, **kwargs)

class ContactViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows contacts to be created by users and managed by admins.
    POST: Public access - Anyone can submit a contact form
    GET, DELETE: Admin access only
    """
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    
    def get_permissions(self):
        if self.action == 'create':  # POST request
            permission_classes = []  # No authentication needed for creating contact
        else:  # GET and DELETE requests
            permission_classes = [permissions.IsAdminUser]  # Only admin can list and delete
        return [permission() for permission in permission_classes]
    
    def update(self, request, *args, **kwargs):
        # Prevent PUT and PATCH methods
        return Response({"detail": "Method not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        # Prevent PUT and PATCH methods
        return Response({"detail": "Method not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

class SiteSettingsViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.UpdateModelMixin):
    """
    API endpoint for managing site settings (singleton pattern).
    GET and PATCH methods require admin authentication.
    """
    queryset = SiteSettings.objects.all()
    serializer_class = SiteSettingsSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_object(self):
        """
        Always return the singleton instance (pk=1).
        """
        return SiteSettings.get_settings()
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/properties/site-settings/
        Get the current site settings (admin only).
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/properties/site-settings/
        Update the site settings (admin only).
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """
        PUT method is not allowed - use PATCH instead.
        """
        return Response(
            {"detail": "Method 'PUT' not allowed. Use 'PATCH' instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
