from rest_framework import serializers
from .models import Feature, PropertyType, Property, PropertyImage, State, District, City, HeroBanner, OfferBanner, Contact, SiteSettings

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['id', 'name']

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ['id', 'name', 'state']

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'district']

class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ['id', 'name']

class PropertyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyType
        fields = ['id', 'name']

class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ['id', 'image']

class PropertySerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True, required=False
    )
    state = serializers.CharField(write_only=True, required=False)
    district = serializers.CharField(write_only=True, required=False)
    city = serializers.CharField(write_only=True, required=False)
    
    # Property type fields
    property_type = serializers.PrimaryKeyRelatedField(queryset=PropertyType.objects.all(), write_only=True, required=False)
    property_type_details = PropertyTypeSerializer(source='property_type', read_only=True)
    
    # Feature fields
    features = serializers.PrimaryKeyRelatedField(queryset=Feature.objects.all(), many=True, write_only=True, required=False)
    feature_details = FeatureSerializer(source='features', many=True, read_only=True)
    
    # Location fields
    location = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = [
            'id', 'property_for', 'property_ownership', 'contact_name', 
            'whatsapp_number', 'phone_number', 'email', 
            'location', 'state', 'district', 'city',
            'title', 'price', 'property_type', 'property_type_details', 'bedrooms', 
            'bathrooms', 'area', 'area_unit', 'description', 'features', 'feature_details', 'google_maps_url', 
            'google_embedded_map_link', 'youtube_video_link', 'latitude', 'longitude',
            'nearby_places', 'built_year', 'furnishing', 'parking_spaces', 'images', 
            'uploaded_images', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')
        extra_kwargs = {
            'state': {'write_only': True},
            'district': {'write_only': True},
            'city': {'write_only': True}
        }

    def get_location(self, obj):
        """Return location information in a structured format"""
        return {
            'state': obj.state.name if obj.state else None,
            'district': obj.district.name if obj.district else None,
            'city': obj.city.name if obj.city else None
        }

    def _process_location_data(self, data):
        """Helper method to process location data"""
        location_fields = {}
        
        state_name = data.pop('state', None)
        district_name = data.pop('district', None)
        city_name = data.pop('city', None)

        # For create operations, require all location fields
        if self.context['request'].method == 'POST':
            if not state_name:
                raise serializers.ValidationError({"state": "State is required"})
            if not district_name:
                raise serializers.ValidationError({"district": "District is required"})
            if not city_name:
                raise serializers.ValidationError({"city": "City is required"})

        # Process location fields only if they are provided
        if state_name:
            state, _ = State.objects.get_or_create(name=state_name)
            location_fields['state'] = state

            if district_name:
                district, _ = District.objects.get_or_create(
                    name=district_name,
                    state=state
                )
                location_fields['district'] = district

                if city_name:
                    city, _ = City.objects.get_or_create(
                        name=city_name,
                        district=district
                    )
                    location_fields['city'] = city

        return location_fields

    def create(self, validated_data):
        # Process location data
        location_fields = self._process_location_data(validated_data)
        validated_data.update(location_fields)
        
        uploaded_images = validated_data.pop('uploaded_images', [])
        features = validated_data.pop('features', [])
        
        property_instance = Property.objects.create(**validated_data)
        
        # Add features
        if features:
            property_instance.features.set(features)
        
        # Create property images
        for image in uploaded_images:
            PropertyImage.objects.create(property=property_instance, image=image)
        
        return property_instance

    def update(self, instance, validated_data):
        # Process location data
        location_fields = self._process_location_data(validated_data.copy())
        
        # Remove location string fields if they exist
        validated_data.pop('state', None)
        validated_data.pop('district', None)
        validated_data.pop('city', None)
        
        # Update location fields if they were processed
        if location_fields.get('state'):
            instance.state = location_fields['state']
        if location_fields.get('district'):
            instance.district = location_fields['district']
        if location_fields.get('city'):
            instance.city = location_fields['city']
        
        # Handle related fields
        uploaded_images = validated_data.pop('uploaded_images', [])
        features = validated_data.pop('features', None)
        
        # Update all other fields
        for attr, value in validated_data.items():
            if hasattr(instance, attr):
                setattr(instance, attr, value)
        
        # Save the instance after updating fields
        instance.save()
        
        # Update features if provided
        if features is not None:
            instance.features.set(features)
        
        # Add new images if provided
        for image in uploaded_images:
            PropertyImage.objects.create(property=instance, image=image)
        
        return instance

class HeroBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroBanner
        fields = ['id', 'image', 'created_at']

class OfferBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferBanner
        fields = ['id', 'image', 'created_at']

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'name', 'email', 'phone_number', 'subject', 'budget_range', 'message', 'created_at']
        read_only_fields = ['created_at']

class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ['id', 'filter_radius', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']




