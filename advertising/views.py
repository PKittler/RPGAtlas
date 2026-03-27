from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from maps.models import Map

from .forms import AdCampaignForm, AdIconForm, AdPartnerForm
from .models import AdCampaign, AdIcon, AdPartner


# ---------------------------------------------------------------------------
# Hilfsfunktion
# ---------------------------------------------------------------------------

def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'Zugriff verweigert.')
            return redirect('home')
        return func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# AdPartner
# ---------------------------------------------------------------------------

@admin_required
def partner_list(request):
    partners = AdPartner.objects.annotate(campaign_count=Count('campaigns')).order_by('name')
    return render(request, 'advertising/partner_list.html', {'partners': partners})


@admin_required
def partner_create(request):
    form = AdPartnerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        partner = form.save()
        messages.success(request, f'Werbepartner „{partner.name}" erstellt.')
        return redirect('adminpanel:advertising:partner_list')
    return render(request, 'advertising/partner_create.html', {'form': form})


@admin_required
def partner_edit(request, pk):
    partner = get_object_or_404(AdPartner, pk=pk)
    form = AdPartnerForm(request.POST or None, instance=partner)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Werbepartner „{partner.name}" aktualisiert.')
        return redirect('adminpanel:advertising:partner_list')
    return render(request, 'advertising/partner_edit.html', {
        'form': form,
        'partner': partner,
    })


@admin_required
def partner_delete(request, pk):
    partner = get_object_or_404(AdPartner, pk=pk)
    if request.method == 'POST':
        name = partner.name
        partner.delete()
        messages.success(request, f'Werbepartner „{name}" gelöscht.')
        return redirect('adminpanel:advertising:partner_list')
    return render(request, 'advertising/partner_delete.html', {'partner': partner})


# ---------------------------------------------------------------------------
# AdCampaign
# ---------------------------------------------------------------------------

@admin_required
def campaign_list(request):
    campaigns = (
        AdCampaign.objects
        .select_related('partner')
        .annotate(icon_count=Count('icons'))
        .order_by('-start_date')
    )
    return render(request, 'advertising/campaign_list.html', {'campaigns': campaigns})


@admin_required
def campaign_create(request):
    form = AdCampaignForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        campaign = form.save()
        messages.success(request, f'Kampagne „{campaign.title}" erstellt.')
        return redirect('adminpanel:advertising:campaign_list')
    return render(request, 'advertising/campaign_create.html', {'form': form})


@admin_required
def campaign_edit(request, pk):
    campaign = get_object_or_404(AdCampaign, pk=pk)
    form = AdCampaignForm(request.POST or None, instance=campaign)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Kampagne „{campaign.title}" aktualisiert.')
        return redirect('adminpanel:advertising:campaign_list')
    return render(request, 'advertising/campaign_edit.html', {
        'form': form,
        'campaign': campaign,
    })


@admin_required
@require_POST
def campaign_deactivate(request, pk):
    campaign = get_object_or_404(AdCampaign, pk=pk)
    campaign.is_active = False
    campaign.save(update_fields=['is_active'])
    messages.success(request, f'Kampagne „{campaign.title}" deaktiviert.')
    return redirect('adminpanel:advertising:campaign_list')


@admin_required
def campaign_delete(request, pk):
    campaign = get_object_or_404(AdCampaign, pk=pk)
    if request.method == 'POST':
        title = campaign.title
        campaign.delete()
        messages.success(request, f'Kampagne „{title}" gelöscht.')
        return redirect('adminpanel:advertising:campaign_list')
    return render(request, 'advertising/campaign_delete.html', {'campaign': campaign})


# ---------------------------------------------------------------------------
# AdIcon
# ---------------------------------------------------------------------------

@admin_required
def icon_list(request):
    icons = (
        AdIcon.objects
        .select_related('campaign', 'campaign__partner', 'map', 'map__map_set')
        .order_by('-created_at')
    )
    return render(request, 'advertising/icon_list.html', {'icons': icons})


@admin_required
def icon_create(request):
    form = AdIconForm(request.POST or None)
    # Alle Karten für die Positions-Vorschau laden
    maps = Map.objects.select_related('map_set').order_by('map_set__title', 'title')
    if request.method == 'POST' and form.is_valid():
        icon = form.save()
        messages.success(request, 'Werbe-Icon erstellt.')
        return redirect('adminpanel:advertising:icon_list')
    return render(request, 'advertising/icon_create.html', {
        'form': form,
        'maps': maps,
    })


@admin_required
def icon_edit(request, pk):
    icon = get_object_or_404(AdIcon, pk=pk)
    form = AdIconForm(request.POST or None, instance=icon)
    maps = Map.objects.select_related('map_set').order_by('map_set__title', 'title')
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Werbe-Icon aktualisiert.')
        return redirect('adminpanel:advertising:icon_list')
    return render(request, 'advertising/icon_edit.html', {
        'form': form,
        'icon': icon,
        'maps': maps,
    })


@admin_required
@require_POST
def icon_deactivate(request, pk):
    icon = get_object_or_404(AdIcon, pk=pk)
    icon.is_active = False
    icon.save(update_fields=['is_active'])
    messages.success(request, 'Werbe-Icon deaktiviert.')
    return redirect('adminpanel:advertising:icon_list')


@admin_required
def icon_delete(request, pk):
    icon = get_object_or_404(AdIcon, pk=pk)
    if request.method == 'POST':
        icon.delete()
        messages.success(request, 'Werbe-Icon gelöscht.')
        return redirect('adminpanel:advertising:icon_list')
    return render(request, 'advertising/icon_delete.html', {'icon': icon})


# ---------------------------------------------------------------------------
# Icon-Vorschau-Daten (AJAX für Position-Picker)
# ---------------------------------------------------------------------------

@admin_required
def icon_map_preview(request, map_pk):
    """Gibt Vorschau-Daten für eine Karte als JSON zurück (für den Positions-Picker)."""
    from django.http import JsonResponse
    map_obj = get_object_or_404(Map.objects.select_related('map_set'), pk=map_pk)
    data = {
        'map_type': map_obj.map_set.map_type,
        'image_url': request.build_absolute_uri(map_obj.image.url) if map_obj.image else None,
        'title': map_obj.title,
    }
    return JsonResponse(data)
