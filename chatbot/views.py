import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decouple import config
from google import genai

from .models import ChatMessage
from .context_builder import build_user_context
from django.utils import timezone
from datetime import timedelta

client = genai.Client(api_key=config('GEMINI_API_KEY'))


@login_required
@require_POST
def chatbot_ask(request):
    data = json.loads(request.body)
    user_message = data.get('message', '').strip()

    if not user_message:
        return JsonResponse({'error': 'Message vide'}, status=400)

    context_text = build_user_context(request.user, user_message)

    system_prompt = f"""Tu es l'assistant du système de gestion de projet (PMS) de Leoni.
Tu réponds UNIQUEMENT à partir des données ci-dessous concernant l'utilisateur connecté.
Ne jamais inventer d'information qui n'est pas dans ces données.
Réponds en français, de façon concise et professionnelle.

Données de l'utilisateur ({request.user.username}, rôle: {request.user.role}) :
{context_text}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=user_message,
        config={
            "system_instruction": system_prompt,
            "max_output_tokens": 500,
        }
    )

    answer = response.text

    ChatMessage.objects.create(
        user=request.user,
        message=user_message,
        response=answer
    )

    return JsonResponse({'response': answer})


@login_required
def chatbot_history(request):
    cutoff = timezone.now() - timedelta(hours=24)
    messages = ChatMessage.objects.filter(
        user=request.user,
        created_at__gte=cutoff
    ).order_by('created_at')

    data = [
        {"message": m.message, "response": m.response}
        for m in messages
    ]
    return JsonResponse({"history": data})