from django.urls import path
from .views import ai_config, log_ai_call, whatsapp_inbound

urlpatterns = [
    path("internal/ai-config", ai_config),
    path("internal/ai-calls", log_ai_call),
    path("whatsapp/inbound", whatsapp_inbound),
]
