from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class CustomAuthMiddleware(MiddlewareMixin):
    """
    Custom middleware to handle authentication for API requests
    """
    
    def process_request(self, request):
        # Skip for non-API requests
        if not request.path.startswith('/api/'):
            return None
            
        # Handle preflight OPTIONS requests
        if request.method == 'OPTIONS':
            response = JsonResponse({})
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            return response
        
        # Try to authenticate using token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]
            try:
                token = Token.objects.get(key=token_key)
                request.user = token.user
                logger.debug(f"User authenticated via token: {request.user.username}")
            except Token.DoesNotExist:
                logger.warning(f"Invalid token provided: {token_key}")
                request.user = None
        
        # Try to authenticate using session (for admin interface)
        elif not request.user.is_authenticated:
            # Check if user is authenticated via session
            if hasattr(request, 'user') and request.user.is_authenticated:
                logger.debug(f"User authenticated via session: {request.user.username}")
            else:
                logger.debug("No authentication found")
        
        return None

    def process_response(self, request, response):
        # Add CORS headers to all API responses
        if request.path.startswith('/api/'):
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response['Access-Control-Allow-Credentials'] = 'true'
        
        return response

