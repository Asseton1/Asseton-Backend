from django.db import models
from django.core.validators import RegexValidator

class State(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class District(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name}, {self.state.name}"

class City(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name}, {self.district.name}"

class Feature(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class PropertyType(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Property(models.Model):
    PROPERTY_FOR_CHOICES = [
        ('rent', 'Rent'),
        ('sell', 'Sell'),
    ]
    
    OWNERSHIP_CHOICES = [
        ('management', 'Management'),
        ('direct_owner', 'Direct Owner'),
    ]
    
    # Basic Information
    property_for = models.CharField(max_length=10, choices=PROPERTY_FOR_CHOICES)
    property_ownership = models.CharField(max_length=20, choices=OWNERSHIP_CHOICES)
    
    # Contact Information
    contact_name = models.CharField(max_length=100)
    whatsapp_number = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    
    # Location Information
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='properties')
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='properties')
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='properties')
    
    # Property Information
    title = models.CharField(max_length=200)
    price = models.TextField(help_text="Price can be numeric (e.g., '2500000') or text (e.g., '25 Lakh', 'Negotiable', 'Contact for price')")
    property_type = models.ForeignKey(PropertyType, on_delete=models.CASCADE, related_name='properties')
    
    # Location Coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Property Details
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    area = models.PositiveIntegerField(help_text="Area in square feet")
    description = models.TextField()
    features = models.ManyToManyField(Feature, related_name='properties')
    google_maps_url = models.URLField(blank=True, null=True)
    google_embedded_map_link = models.TextField(blank=True, null=True, help_text="Paste the complete iframe HTML code from Google Maps embed")
    youtube_video_link = models.URLField(blank=True, null=True)
    nearby_places = models.JSONField(blank=True, null=True, help_text="List of nearby places in format: ['place1 - 1km', 'place2 - 2km']")
    built_year = models.PositiveIntegerField()
    furnishing = models.CharField(max_length=50)
    parking_spaces = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
        
class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.property.title}"

class HeroBanner(models.Model):
    image = models.ImageField(upload_to='banners/hero/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Hero Banner {self.id}"

class OfferBanner(models.Model):
    image = models.ImageField(upload_to='banners/offers/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Offer Banner {self.id}"

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    subject = models.CharField(max_length=200)
    budget_range = models.CharField(max_length=100, null=True, blank=True, help_text="e.g., '₹50,000 - ₹1,00,000' or '$500 - $1000'")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.subject}"

    class Meta:
        ordering = ['-created_at']  # Most recent contacts first
