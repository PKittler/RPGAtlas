from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AdminUserCreateForm,
    AdminUserEditForm,
    LoginForm,
    PasswordChangeForm,
    ProfileEditForm,
    RegistrationForm,
)
from .models import User


# ---------------------------------------------------------------------------
# Hilfsfunktionen / Dekoratoren
# ---------------------------------------------------------------------------

def admin_required(func):
    """Dekorator: Zugriff nur für eingeloggte Nutzer mit role='admin'."""
    @wraps(func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'Zugriff verweigert.')
            return redirect('home')
        return func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Öffentliche Auth-Views
# ---------------------------------------------------------------------------

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Willkommen, {user.username}! Registrierung erfolgreich.')
        return redirect('home')

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_banned:
                messages.error(request, 'Dein Account wurde gesperrt. Bitte kontaktiere den Support.')
            else:
                login(request, user)
                next_url = request.GET.get('next', '/')
                return redirect(next_url)
        else:
            messages.error(request, 'E-Mail oder Passwort ist falsch.')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'Du wurdest ausgeloggt.')
        return redirect('accounts:login')
    return redirect('home')


# ---------------------------------------------------------------------------
# Eingeloggte User-Views
# ---------------------------------------------------------------------------

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')


@login_required
def profile_edit_view(request):
    profile_form = ProfileEditForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileEditForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profil aktualisiert.')
                return redirect('accounts:profile')
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                # Session nach Passwortänderung neu einloggen
                login(request, request.user)
                messages.success(request, 'Passwort erfolgreich geändert.')
                return redirect('accounts:profile')

    return render(request, 'accounts/profile_edit.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })


@login_required
def delete_account_view(request):
    if request.method == 'POST':
        password = request.POST.get('password', '')
        user = request.user
        if user.check_password(password):
            logout(request)
            user.soft_delete()
            messages.success(request, 'Dein Account wurde gelöscht.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Das Passwort ist falsch.')

    return render(request, 'accounts/delete_account.html')


# ---------------------------------------------------------------------------
# Admin-Views (nur role='admin')
# ---------------------------------------------------------------------------

@admin_required
def admin_user_list(request):
    query = request.GET.get('q', '').strip()
    users = User.objects.filter(deleted_at__isnull=True)
    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        )
    users = users.order_by('username')
    return render(request, 'accounts/admin/user_list.html', {
        'users': users,
        'query': query,
    })


@admin_required
def admin_user_edit(request, user_id):
    target_user = get_object_or_404(User, pk=user_id, deleted_at__isnull=True)
    form = AdminUserEditForm(request.POST or None, instance=target_user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Benutzer „{target_user.username}" aktualisiert.')
        return redirect('accounts:admin_user_list')
    return render(request, 'accounts/admin/user_edit.html', {
        'form': form,
        'target_user': target_user,
    })


@admin_required
def admin_user_create(request):
    form = AdminUserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Benutzer „{user.username}" erstellt.')
        return redirect('accounts:admin_user_list')
    return render(request, 'accounts/admin/user_create.html', {'form': form})


@admin_required
def admin_user_delete(request, user_id):
    target_user = get_object_or_404(User, pk=user_id, deleted_at__isnull=True)
    if request.method == 'POST':
        username = target_user.username
        target_user.soft_delete()
        messages.success(request, f'Benutzer „{username}" gelöscht.')
        return redirect('accounts:admin_user_list')
    return render(request, 'accounts/admin/user_delete.html', {
        'target_user': target_user,
    })
