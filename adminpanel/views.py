from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.forms import AdminUserCreateForm, AdminUserEditForm
from accounts.models import User
from advertising.models import AdCampaign
from maps.models import MapSet
from sessions.models import GameSession


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def admin_required(func):
    """Dekorator: Zugriff nur für role='admin'."""
    @wraps(func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'Zugriff verweigert. Nur Administratoren können das Admin-Panel nutzen.')
            return redirect('home')
        return func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_required
def dashboard(request):
    today = timezone.now().date()

    total_users = User.objects.filter(deleted_at__isnull=True).count()
    active_users = User.objects.filter(deleted_at__isnull=True, is_active=True, is_banned=False).count()
    banned_users = User.objects.filter(deleted_at__isnull=True, is_banned=True).count()
    total_mapsets = MapSet.objects.count()
    running_sessions = GameSession.objects.filter(status='running').count()
    active_campaigns = AdCampaign.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
    ).count()

    return render(request, 'adminpanel/dashboard.html', {
        'total_users': total_users,
        'active_users': active_users,
        'banned_users': banned_users,
        'total_mapsets': total_mapsets,
        'running_sessions': running_sessions,
        'active_campaigns': active_campaigns,
    })


# ---------------------------------------------------------------------------
# User-Verwaltung
# ---------------------------------------------------------------------------

@admin_required
def user_list(request):
    query = request.GET.get('q', '').strip()
    users = User.objects.filter(deleted_at__isnull=True)
    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        )
    users = users.order_by('username')
    return render(request, 'adminpanel/user_list.html', {
        'users': users,
        'query': query,
    })


@admin_required
def user_create(request):
    form = AdminUserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Benutzer „{user.username}" erstellt.')
        return redirect('adminpanel:user_list')
    return render(request, 'adminpanel/user_create.html', {'form': form})


@admin_required
def user_edit(request, pk):
    target_user = get_object_or_404(User, pk=pk, deleted_at__isnull=True)
    form = AdminUserEditForm(request.POST or None, instance=target_user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Benutzer „{target_user.username}" aktualisiert.')
        return redirect('adminpanel:user_list')
    return render(request, 'adminpanel/user_edit.html', {
        'form': form,
        'target_user': target_user,
    })


@admin_required
def user_delete(request, pk):
    target_user = get_object_or_404(User, pk=pk, deleted_at__isnull=True)
    if request.method == 'POST':
        if target_user == request.user:
            messages.error(request, 'Du kannst deinen eigenen Account nicht löschen.')
            return redirect('adminpanel:user_list')
        username = target_user.username
        target_user.soft_delete()
        messages.success(request, f'Benutzer „{username}" DSGVO-konform gelöscht.')
        return redirect('adminpanel:user_list')
    return render(request, 'adminpanel/user_delete.html', {'target_user': target_user})


# ---------------------------------------------------------------------------
# Karten-Set-Verwaltung
# ---------------------------------------------------------------------------

@admin_required
def mapset_list(request):
    mapsets = (
        MapSet.objects
        .select_related('owner')
        .annotate(map_count=Count('maps'))
        .order_by('-created_at')
    )
    return render(request, 'adminpanel/mapset_list.html', {'mapsets': mapsets})


@admin_required
def mapset_delete(request, pk):
    mapset = get_object_or_404(MapSet, pk=pk)
    if request.method == 'POST':
        title = mapset.title
        mapset.delete()
        messages.success(request, f'Karten-Set „{title}" gelöscht.')
        return redirect('adminpanel:mapset_list')
    return render(request, 'adminpanel/mapset_delete.html', {'mapset': mapset})
