from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)

class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access for unauthenticated users
    and full access for authenticated users.
    """
    
    def has_permission(self, request, view):
        # Allow read-only access for unauthenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Require authentication for write operations
        if request.user and request.user.is_authenticated:
            logger.debug(f"Authenticated user {request.user.username} attempting {request.method}")
            return True
        
        logger.warning(f"Unauthenticated user attempting {request.method} on {request.path}")
        return False

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access for all users
    and full access for admin users only.
    """
    
    def has_permission(self, request, view):
        # Allow read-only access for all users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Require admin access for write operations
        if request.user and request.user.is_authenticated and request.user.is_staff:
            logger.debug(f"Admin user {request.user.username} attempting {request.method}")
            return True
        
        logger.warning(f"Non-admin user attempting {request.method} on {request.path}")
        return False

class FlexibleAuthentication(permissions.BasePermission):
    """
    Flexible authentication that allows both token and session authentication
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated via any method
        if request.user and request.user.is_authenticated:
            logger.debug(f"User {request.user.username} authenticated via {type(request.user)}")
            return True
        
        # For read operations, allow unauthenticated access
        if request.method in permissions.SAFE_METHODS:
            logger.debug(f"Allowing read access for unauthenticated user")
            return True
        
        logger.warning(f"Unauthenticated user attempting {request.method} on {request.path}")
        return False
