from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import RegisterForm
from django.shortcuts import render, redirect, get_object_or_404
from .decorators import admin_required
from .forms import UserCreateForm, UserUpdateForm
from .models import User


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Compte créé avec succès. Vous pouvez vous connecter.")
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

def redirect_by_role(user):
    """Redirige vers le bon dashboard selon le rôle de l'utilisateur."""
    role_redirects = {
        'ADMIN': 'admin_dashboard',
        'PM': 'pm_dashboard',
        'USER': 'user_dashboard',
    }
    url_name = role_redirects.get(user.role, 'dashboard')  # fallback si rôle inconnu
    return redirect(url_name)
def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('accounts:login')




@admin_required
def user_list_view(request):
    users = User.objects.all().order_by('username')
    return render(request, 'accounts/user_list.html', {'users': users})


@admin_required
def user_create_view(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur créé avec succès.")
            return redirect('accounts:user_list')
    else:
        form = UserCreateForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Nouvel utilisateur'})


@admin_required
def user_update_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur modifié avec succès.")
            return redirect('accounts:user_list')
    else:
        form = UserUpdateForm(instance=user_obj)
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Modifier utilisateur'})


@admin_required
def user_delete_view(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, "Utilisateur supprimé.")
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_delete.html', {'user_obj': user_obj})