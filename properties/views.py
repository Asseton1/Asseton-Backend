import logging
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
import math
from urllib.parse import urlencode

from collections import defaultdict

from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Q, Case, When, Prefetch, Min
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, viewsets, permissions, mixins, status
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
    PropertyListSerializer,
    PropertyImageSerializer,
    StateSerializer,
    DistrictSerializer,
    CitySerializer,
    HeroBannerSerializer,
    OfferBannerSerializer,
    ContactSerializer,
    SiteSettingsSerializer,
    PropertyLocationSerializer,
)
from .utils import (
    haversine_km,
    locations_cache_key,
    LOCATIONS_CACHE_TTL,
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
        return Response({"detail": "Method 'PUT' not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
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
        return Response({"detail": "Method 'PUT' not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
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
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    pagination_class = PropertyPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'locations']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'list':
            return PropertyListSerializer
        return PropertySerializer

    def _list_image_prefetch(self, pks):
        """
        Prefetch only the first image per property for list cards.
        (Django Prefetch forbids sliced querysets, so resolve first image ids explicitly.)
        Features are omitted — not on PropertyListSerializer.
        """
        first_image_ids = list(
            PropertyImage.objects.filter(property_id__in=pks)
            .values('property_id')
            .annotate(min_id=Min('id'))
            .values_list('min_id', flat=True)
        )
        return Prefetch(
            'images',
            queryset=PropertyImage.objects.filter(id__in=first_image_ids).order_by('id'),
        )

    def _is_admin_fast_list(self, request):
        """Admin UI opt-in; does not change default public list behavior."""
        mode = (request.query_params.get('search_mode') or '').strip().lower()
        return mode in ('admin', 'lite')

    def _admin_fast_list(self, request):
        """
        Fast admin property list/search.

        Avoids JOIN+ORDER BY+COUNT that Azure MySQL turns into multi-second plans:
        - Location/type name matches resolved via small ID lookups, then OR on FK ids
        - Pagination uses values_list(pk) + page_size+1 for next-page detection
        - Response shape stays DRF-compatible: count/next/previous/results
        """
        params = request.query_params
        try:
            page_size = int(params.get('page_size', PropertyPagination.page_size))
        except (TypeError, ValueError):
            page_size = PropertyPagination.page_size
        page_size = max(1, min(page_size, PropertyPagination.max_page_size))
        try:
            page = max(1, int(params.get('page', 1)))
        except (TypeError, ValueError):
            page = 1

        qs = Property.objects.all()

        user = request.user
        is_staff = user.is_authenticated and getattr(user, 'is_staff', False)
        moderation_status = params.get('moderation_status')
        if is_staff:
            if moderation_status in dict(Property.MODERATION_STATUS_CHOICES):
                qs = qs.filter(moderation_status=moderation_status)
        else:
            qs = qs.filter(moderation_status='approved')

        property_for = (params.get('property_for') or '').strip().lower()
        if property_for in dict(Property.PROPERTY_FOR_CHOICES):
            qs = qs.filter(property_for=property_for)

        search = (params.get('search') or '').strip()
        if search:
            search_terms = [term.strip() for term in search.split() if term.strip()]
            for term in search_terms:
                type_ids = list(
                    PropertyType.objects.filter(name__icontains=term).values_list('id', flat=True)[:50]
                )
                state_ids = list(
                    State.objects.filter(name__icontains=term).values_list('id', flat=True)[:50]
                )
                district_ids = list(
                    District.objects.filter(name__icontains=term).values_list('id', flat=True)[:50]
                )
                city_ids = list(
                    City.objects.filter(name__icontains=term).values_list('id', flat=True)[:50]
                )
                term_query = (
                    Q(title__icontains=term)
                    | Q(contact_name__icontains=term)
                )
                if type_ids:
                    term_query |= Q(property_type_id__in=type_ids)
                if state_ids:
                    term_query |= Q(state_id__in=state_ids)
                if district_ids:
                    term_query |= Q(district_id__in=district_ids)
                if city_ids:
                    term_query |= Q(city_id__in=city_ids)
                qs = qs.filter(term_query)

        # Property table only — no JOINs for sort/page.
        total_count = qs.count()
        qs = qs.order_by('-created_at')
        offset = (page - 1) * page_size
        # Fetch one extra row instead of COUNT for pagination (has_next only).
        id_page = list(qs.values_list('pk', flat=True)[offset:offset + page_size + 1])
        has_next = len(id_page) > page_size
        pks = id_page[:page_size]

        if not pks:
            serializer = self.get_serializer([], many=True)
            return Response({
                'count': total_count,
                'next': None,
                'previous': None,
                'results': serializer.data,
            })

        order = Case(*[When(pk=pk, then=i) for i, pk in enumerate(pks)])
        page_qs = (
            Property.objects.filter(pk__in=pks)
            .select_related('state', 'district', 'city', 'property_type')
            .prefetch_related(self._list_image_prefetch(pks))
            .order_by(order)
        )
        serializer = self.get_serializer(page_qs, many=True)

        base_url = request.build_absolute_uri(request.path)

        def page_url(p):
            q = {'page': p, 'page_size': page_size, 'search_mode': 'admin'}
            if search:
                q['search'] = search
            if property_for:
                q['property_for'] = property_for
            if moderation_status:
                q['moderation_status'] = moderation_status
            return f"{base_url}?{urlencode(q)}"

        return Response({
            'count': total_count,
            'next': page_url(page + 1) if has_next else None,
            'previous': page_url(page - 1) if page > 1 else None,
            'results': serializer.data,
        })

    def list(self, request, *args, **kwargs):
        """
        Paginate with a fast ORDER BY on `properties_property` only, then reload that page
        with select_related + prefetch_related. A single JOIN+ORDER BY+LIMIT on Azure MySQL
        was taking several seconds; PK lookup + joins for ~10 rows is ~0.1s.
        """
        if self._is_admin_fast_list(request):
            return self._admin_fast_list(request)

        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.prefetch_related(None)
        page = self.paginate_queryset(queryset)
        if page is not None:
            pks = [obj.pk for obj in page]
            if not pks:
                serializer = self.get_serializer([], many=True)
                return self.get_paginated_response(serializer.data)
            order = Case(*[When(pk=pk, then=i) for i, pk in enumerate(pks)])
            page_qs = (
                Property.objects.filter(pk__in=pks)
                .select_related('state', 'district', 'city', 'property_type')
                .prefetch_related(self._list_image_prefetch(pks))
                .order_by(order)
            )
            serializer = self.get_serializer(page_qs, many=True)
            return self.get_paginated_response(serializer.data)
        pks = list(queryset.values_list('pk', flat=True))
        if not pks:
            serializer = self.get_serializer([], many=True)
            return Response(serializer.data)
        order = Case(*[When(pk=pk, then=i) for i, pk in enumerate(pks)])
        full_qs = (
            Property.objects.filter(pk__in=pks)
            .select_related('state', 'district', 'city', 'property_type')
            .prefetch_related(self._list_image_prefetch(pks))
            .order_by(order)
        )
        serializer = self.get_serializer(full_qs, many=True)
        return Response(serializer.data)

    def _normalize_create_data(self, request):
        """Ensure uploaded_images and features are lists for multipart (multiple files/IDs)."""
        data = request.data
        has_multipart = hasattr(data, 'getlist')
        # Normalize uploaded_images to a list
        if has_multipart:
            files = data.getlist('uploaded_images')
            if not files and data.get('uploaded_images'):
                files = [data.get('uploaded_images')]
        else:
            files = data.get('uploaded_images')
            if not isinstance(files, list):
                files = [files] if files else []
        # Normalize features to a list (FormData sends multiple "features" keys; QueryDict.get returns only the last)
        if has_multipart:
            features = data.getlist('features')
        else:
            features = data.get('features')
            if features is None:
                features = []
            elif not isinstance(features, list):
                features = [features] if features else []
        out = {}
        for key in data:
            if key == 'uploaded_images':
                out[key] = files
            elif key == 'features':
                out[key] = features
            else:
                out[key] = data.get(key)
        return out

    def create(self, request, *args, **kwargs):
        try:
            data = self._normalize_create_data(request)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except serializers.ValidationError:
            raise  # Let DRF return 400 with validation errors
        except IntegrityError as e:
            return Response(
                {"detail": "Invalid or duplicate data: " + str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logging.exception("Property create failed")
            return Response(
                {
                    "detail": str(e),
                    "error_type": type(e).__name__,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'], url_path='locations')
    def locations(self, request):
        """
        GET /api/properties/locations/
        Returns distinct property locations (name + lat/lng) with pagination and search.
        Same-name locations within filter_radius are merged; the first (newest) location's
        coordinates are shown. Ordered by most recently added first.
        Query params: page, page_size, search, property_for (optional: 'rent' or 'sell')
        """
        site_settings = SiteSettings.get_settings()
        filter_radius_km = float(site_settings.filter_radius)

        include_unapproved = (
            request.user.is_authenticated and getattr(request.user, 'is_staff', False)
        )
        property_for = (request.query_params.get('property_for') or '').strip().lower()
        if property_for not in dict(Property.PROPERTY_FOR_CHOICES):
            property_for = ''
        search = (request.query_params.get('search') or '').strip()

        cache_key = locations_cache_key(
            include_unapproved, property_for, search, filter_radius_km
        )
        results = cache.get(cache_key)

        if results is None:
            locations_qs = Property.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False,
            )
            if not include_unapproved:
                locations_qs = locations_qs.filter(moderation_status='approved')
            if property_for:
                locations_qs = locations_qs.filter(property_for=property_for)
            if search:
                locations_qs = locations_qs.filter(
                    Q(state__name__icontains=search)
                    | Q(district__name__icontains=search)
                    | Q(city__name__icontains=search)
                )

            # Lean values() fetch — avoids full ORM hydration for every property.
            rows = list(
                locations_qs.order_by('-created_at').values(
                    'state_id',
                    'district_id',
                    'city_id',
                    'latitude',
                    'longitude',
                    'created_at',
                    'state__name',
                    'district__name',
                    'city__name',
                )
            )

            groups = defaultdict(list)
            for row in rows:
                key = (row['state_id'], row['district_id'], row['city_id'])
                groups[key].append(row)

            results = []
            for _key, props in groups.items():
                # props already sorted by -created_at from queryset order
                clusters = []
                for prop in props:
                    lat1 = prop['latitude']
                    lon1 = prop['longitude']
                    found = False
                    for cluster in clusters:
                        rep = cluster['rep']
                        dist_km = haversine_km(
                            lat1, lon1, rep['latitude'], rep['longitude']
                        )
                        if dist_km <= filter_radius_km:
                            cluster['members'].append(prop)
                            found = True
                            break
                    if not found:
                        clusters.append({'rep': prop, 'members': [prop]})

                for cluster in clusters:
                    rep = cluster['rep']
                    city_name = rep['city__name'] or ''
                    district_name = rep['district__name'] or ''
                    state_name = rep['state__name'] or ''
                    results.append({
                        'location_name': f"{city_name}, {district_name}, {state_name}",
                        'latitude': rep['latitude'],
                        'longitude': rep['longitude'],
                        'state': state_name,
                        'district': district_name,
                        'city': city_name,
                        '_created_at': rep['created_at'],
                    })

            results.sort(key=lambda x: x['_created_at'], reverse=True)
            for r in results:
                del r['_created_at']

            cache.set(cache_key, results, timeout=LOCATIONS_CACHE_TTL)

        # Pagination (applied after clustering; same response shape as before)
        try:
            page_size = int(request.query_params.get('page_size', PropertyPagination.page_size))
        except (TypeError, ValueError):
            page_size = PropertyPagination.page_size
        page_size = max(1, min(page_size, PropertyPagination.max_page_size))
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (TypeError, ValueError):
            page = 1
        count = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        page_results = results[start:end]

        serializer = PropertyLocationSerializer(page_results, many=True)
        base_url = request.build_absolute_uri(request.path)

        def pagination_url(p):
            params = {'page': p, 'page_size': page_size}
            if search:
                params['search'] = search
            if property_for:
                params['property_for'] = property_for
            return f"{base_url}?{urlencode(params)}"

        next_url = None if end >= count else pagination_url(page + 1)
        prev_url = None if page <= 1 else pagination_url(page - 1)

        return Response({
            "count": count,
            "next": next_url,
            "previous": prev_url,
            "results": serializer.data,
        })

    def get_queryset(self):
        queryset = super().get_queryset()
        # list: avoid select_related — combined JOIN + ORDER BY + LIMIT made Azure MySQL use a ~4s plan.
        # Other actions still prefetch FKs in one round-trip per object.
        if self.action != 'list':
            queryset = queryset.select_related('state', 'district', 'city', 'property_type')

        user = self.request.user
        is_staff = user.is_authenticated and user.is_staff
        moderation_status = self.request.query_params.get('moderation_status')

        if is_staff:
            if moderation_status in dict(Property.MODERATION_STATUS_CHOICES):
                queryset = queryset.filter(moderation_status=moderation_status)
        elif self.action in ('list', 'locations'):
            queryset = queryset.filter(moderation_status='approved')
        elif self.action == 'retrieve' and not user.is_authenticated:
            queryset = queryset.filter(moderation_status='approved')

        params = self.request.query_params

        price_min = params.get('price_min')
        price_max = params.get('price_max')
        property_for = params.get('property_for')
        ownership = params.get('ownership')
        area_min = params.get('area_min')
        area_max = params.get('area_max')
        area_unit_param = params.get('area_unit')
        area_unit = (area_unit_param or '').strip().lower() or None
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
        # Search OR-clauses include features (M2M); DISTINCT is required then only.
        # Unconditional DISTINCT made every list query a heavy SELECT DISTINCT over Azure MySQL (~4s+).
        search_needs_distinct = False

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

        # Price filtering: price is TextField and can contain non-numeric values
        # Apply filtering in Python for rows where price is a pure numeric string
        price_min_decimal = convert_decimal(price_min)
        price_max_decimal = convert_decimal(price_max)
        if price_min_decimal is not None or price_max_decimal is not None:
            # Invalid range: min > max returns no results
            if (
                price_min_decimal is not None
                and price_max_decimal is not None
                and price_min_decimal > price_max_decimal
            ):
                return queryset.none()

            matching_ids = []
            for row in queryset.values("id", "price"):
                raw_price = (row.get("price") or "").strip()
                try:
                    numeric_price = Decimal(raw_price)
                except (InvalidOperation, TypeError):
                    # Skip non-numeric prices like "75 lakh", "Negotiable", etc.
                    continue

                if price_min_decimal is not None and numeric_price < price_min_decimal:
                    continue
                if price_max_decimal is not None and numeric_price > price_max_decimal:
                    continue

                matching_ids.append(row["id"])

            if not matching_ids:
                return queryset.none()

            queryset = queryset.filter(id__in=matching_ids)

        if property_for in dict(Property.PROPERTY_FOR_CHOICES):
            queryset = queryset.filter(property_for=property_for)

        if ownership in dict(Property.OWNERSHIP_CHOICES):
            queryset = queryset.filter(property_ownership=ownership)

        if furnishing:
            queryset = queryset.filter(furnishing__iexact=furnishing)

        # Area filtering - filter by matching area_unit and area value (no conversion)
        # Get valid area unit choices as a set for efficient lookup
        valid_area_units = {choice[0] for choice in Property.AREA_UNIT_CHOICES}
        
        # Filter by area_unit if provided and valid
        if area_unit and area_unit in valid_area_units:
            queryset = queryset.filter(area_unit=area_unit)
            
            # Apply area_min and area_max filters only when area_unit is specified
            # This ensures we're comparing within the same unit
            area_min_value = convert_int(area_min)
            if area_min_value is not None:
                queryset = queryset.filter(area__gte=area_min_value)

            area_max_value = convert_int(area_max)
            if area_max_value is not None:
                queryset = queryset.filter(area__lte=area_max_value)
        elif area_min or area_max:
            # If area_min/area_max are provided but area_unit is not, 
            # default to 'sqft' for backward compatibility
            queryset = queryset.filter(area_unit='sqft')
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

        # Support single ID or multiple: property_type=1 or property_type=1,2,3 or property_type=1&property_type=2
        property_type_ids = None
        if property_type is not None:
            # getlist handles repeated params: ?property_type=1&property_type=2
            raw_values = self.request.query_params.getlist('property_type') or [property_type]
            # Also support comma-separated in first value: ?property_type=1,2,3
            parsed = []
            for raw in raw_values:
                for part in str(raw).split(','):
                    part = part.strip()
                    if part:
                        pid = convert_int(part)
                        if pid is not None:
                            parsed.append(pid)
            if parsed:
                property_type_ids = list(dict.fromkeys(parsed))  # unique, preserve order
        if property_type_ids is not None:
            queryset = queryset.filter(property_type_id__in=property_type_ids)

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
                # Admin property list can pass search_mode=admin for a faster path:
                # title/contact/location/type only — no description scan or features M2M DISTINCT.
                # Default (public listing) keeps the full search behavior unchanged.
                search_mode = (params.get('search_mode') or '').strip().lower()
                lite_search = search_mode in ('admin', 'lite')

                combined_query = Q()
                for term in search_terms:
                    if lite_search:
                        term_query = (
                            Q(title__icontains=term)
                            | Q(contact_name__icontains=term)
                            | Q(property_type__name__icontains=term)
                            | Q(state__name__icontains=term)
                            | Q(district__name__icontains=term)
                            | Q(city__name__icontains=term)
                        )
                    else:
                        # Note: nearby_places is JSONField; icontains is not supported, so it's excluded from search
                        term_query = (
                            Q(title__icontains=term)
                            | Q(description__icontains=term)
                            | Q(property_type__name__icontains=term)
                            | Q(contact_name__icontains=term)
                            | Q(features__name__icontains=term)
                            | Q(state__name__icontains=term)
                            | Q(district__name__icontains=term)
                            | Q(city__name__icontains=term)
                            | Q(property_for__icontains=term)
                            | Q(property_ownership__icontains=term)
                            | Q(furnishing__icontains=term)
                            | Q(price__icontains=term)
                        )
                        search_needs_distinct = True
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
                # 1 degree longitude ≈ 111 km * cos(latitude); avoid division by zero near poles
                lat_degree = radius_to_use / Decimal('111.0')
                cos_lat = abs(math.cos(math.radians(float(lat_value))))
                lng_degree = radius_to_use / (Decimal('111.0') * Decimal(str(cos_lat))) if cos_lat >= 1e-9 else Decimal('0')
                
                # Create bounding box
                queryset = queryset.filter(
                    latitude__gte=lat_value - lat_degree,
                    latitude__lte=lat_value + lat_degree,
                    longitude__gte=lng_value - lng_degree,
                    longitude__lte=lng_value + lng_degree
                )

        queryset = queryset.order_by('-created_at')
        if search_needs_distinct:
            queryset = queryset.distinct()
        # Avoid N+1 when serializing nested images and features (critical with remote DB).
        if self.action in ('list', 'retrieve'):
            queryset = queryset.prefetch_related('images', 'features')
        return queryset

    @action(detail=True, methods=['delete'])
    def delete_image(self, request, pk=None):
        """
        Delete a specific image from a property.
        Pass image_id in JSON body (e.g. {"image_id": 1}) or as query param (?image_id=1).
        """
        property_obj = self.get_object()
        # Accept image_id from body or query params (DELETE often has no body)
        image_id = None
        try:
            image_id = request.data.get('image_id') if request.data else None
        except Exception:
            pass
        if image_id is None:
            image_id = request.query_params.get('image_id')
        if image_id is None:
            return Response(
                {"detail": "image_id is required. Pass it in the request body or as query param (e.g. ?image_id=1)."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            image_id = int(image_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "image_id must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            image = PropertyImage.objects.get(id=image_id, property=property_obj)
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
    lookup_field = 'pk'
    lookup_url_kwarg = None
    
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
