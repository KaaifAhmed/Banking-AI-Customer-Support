from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(request):
    return JsonResponse({"success": True, "data": {"status": "ok"}, "error": None})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health),
    path("auth/", include("users.urls")),
    path("api/", include("core.urls")),
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="schema")),
]
