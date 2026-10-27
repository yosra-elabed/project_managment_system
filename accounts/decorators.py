from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != request.user.Role.ADMIN:
            raise PermissionDenied("Réservé aux administrateurs.")
        return view_func(request, *args, **kwargs)
    return wrapper