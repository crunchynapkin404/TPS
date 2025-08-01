"""
URL configuration for tps_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.shortcuts import redirect
from django.http import HttpResponse
from core.views import test_formats_view
from django.views.i18n import set_language
from core.health import health_check, readiness_check, liveness_check, metrics_endpoint

def accounts_login_redirect(request):
    """Redirect /accounts/login/ to /login/"""
    return redirect('/login/')

def favicon_view(request):
    """Serve favicon"""
    return redirect('/static/images/favicon.svg')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', accounts_login_redirect, name='accounts_login_redirect'),
    path('accounts/', include('apps.accounts.urls')),
    path('favicon.ico', favicon_view, name='favicon'),
    path('api/', include('api.urls')),
    path('leave/', include('apps.leave_management.urls')),
    path('test-formats/', test_formats_view, name='test_formats'),  # Test endpoint
    path('set_language/', set_language, name='set_language'),  # Language switching
    
    # Health check endpoints for production monitoring
    path('health/', health_check, name='health_check'),
    path('health/ready/', readiness_check, name='readiness_check'),
    path('health/live/', liveness_check, name='liveness_check'),
    path('metrics/', metrics_endpoint, name='metrics'),
    
    path('', include('frontend.urls')),
]

# Add static files handling for development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Debug toolbar temporarily disabled for cleaner UI
    # import debug_toolbar
    # urlpatterns = [
    #     path('__debug__/', include(debug_toolbar.urls)),
    # ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
