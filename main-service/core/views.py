from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(["GET"])
def ai_config(request):
    # TODO (kickoff): back with a real DB-backed config model + Django Admin
    # — see "Dynamic Configuration" in docs/architecture.md.
    return JsonResponse({
        "success": True,
        "data": {"tiers": {"fast": None, "smart": None}, "fallback_order": []},
        "error": None,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def whatsapp_inbound(request):
    # TODO (kickoff): resolve request.data["phone"] via UserProfile,
    # enqueue onto ai_queue or tasks_queue depending on intent.
    return JsonResponse({"success": True, "data": {"received": True}, "error": None})


@api_view(["POST"])
def log_ai_call(request):
    # TODO (kickoff): persist to a real AICall model instead of just printing
    # — see docs/ai-system.md §4.4 (agent identities) and §6.2 (audit trail).
    print(f"[ai_call telemetry] {request.data}")
    return JsonResponse({"success": True, "data": {"logged": True}, "error": None})
