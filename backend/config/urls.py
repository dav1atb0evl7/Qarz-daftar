import mimetypes
from pathlib import Path
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

FRONTEND_DIR = settings.BASE_DIR.parent / "stitch_qarz_daftar_pro_frontend"

def serve_frontend_file(request, filename="index.html"):
    file_path = FRONTEND_DIR / filename
    if file_path.exists() and file_path.is_file():
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            if filename.endswith(".js"):
                mime_type = "application/javascript"
            elif filename.endswith(".css"):
                mime_type = "text/css"
            elif filename.endswith(".ttf"):
                mime_type = "font/ttf"
            elif filename.endswith(".woff2"):
                mime_type = "font/woff2"
            else:
                mime_type = "text/html"
        resp = HttpResponse(file_path.read_bytes(), content_type=mime_type)
        resp['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp['Pragma'] = 'no-cache'
        resp['Expires'] = '0'
        return resp
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        resp = HttpResponse(index_path.read_bytes(), content_type="text/html")
        resp['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    return JsonResponse({"detail": "Frontend file not found"}, status=404)

def api_root_info(request):
    return JsonResponse({
        "name": "Qarz Daftar Pro Enterprise Ledger API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/api/v1/docs/",
        "swagger": "/api/v1/docs/",
        "endpoints": {
            "auth": "/api/v1/auth/login/",
            "shops": "/api/v1/shops/",
            "customers": "/api/v1/customers/",
            "debts": "/api/v1/debts/",
            "payments": "/api/v1/payments/",
            "reports": "/api/v1/reports/",
            "telegram": "/api/v1/telegram/"
        }
    })

urlpatterns = [
    # Frontend Single Page App Routes on port 8000
    path('', lambda req: serve_frontend_file(req, "index.html"), name='frontend-root'),
    path('index.html', lambda req: serve_frontend_file(req, "index.html"), name='frontend-index'),
    path('app.js', lambda req: serve_frontend_file(req, "app.js"), name='frontend-js'),
    path('styles.css', lambda req: serve_frontend_file(req, "styles.css"), name='frontend-css'),
    re_path(r'^(?P<filename>[a-zA-Z0-9_\-\.]+\.(ttf|woff2|woff|svg|png|jpg|ico|js|css))$', serve_frontend_file, name='frontend-assets'),

    path('admin/', admin.site.urls),

    # OpenAPI Schema & Interactive Docs
    path('api/v1/', api_root_info, name='api-v1-root'),
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Modular API v1 Routes
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/telegram/', include('apps.accounts.telegram_urls')),
    path('api/v1/shops/', include('apps.shops.urls')),
    path('api/v1/customers/', include('apps.customers.urls')),
    path('api/v1/debts/', include('apps.debts.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
