# projects/context_processors.py
from .models import Delegation

def deputy_badge(request):
    if not request.user.is_authenticated:
        return {}
    count = Delegation.objects.filter(deputy=request.user, is_active=True).count()
    return {'my_active_deputy_count': count}