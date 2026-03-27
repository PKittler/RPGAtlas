from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from characters.models import Character
from sessions.models import CharacterPosition

from .models import InventoryItem


def _check_item_permission(request, item):
    """Spielleiter oder Figuren-Besitzer dürfen Items verwalten."""
    from sessions.models import SessionParticipant
    is_gm = SessionParticipant.objects.filter(
        session=item.session,
        user=request.user,
        role='gamemaster',
        is_removed=False,
        is_confirmed=True,
    ).exists()
    is_owner = item.character.owner == request.user
    if not is_gm and not is_owner:
        raise PermissionDenied


@login_required
@require_POST
def item_drop(request, item_pk):
    """Item aus dem Inventar ablegen (löscht InventoryItem)."""
    item = get_object_or_404(
        InventoryItem.objects.select_related('character', 'session'), pk=item_pk,
    )
    _check_item_permission(request, item)
    item.delete()
    response = HttpResponse(status=200)
    response['HX-Trigger'] = 'inventoryUpdated'
    return response


@login_required
def item_transfer_form(request, item_pk):
    """HTMX-Partial: Transfer-Formular für ein Item."""
    item = get_object_or_404(
        InventoryItem.objects.select_related('character', 'session', 'session__active_map'),
        pk=item_pk,
    )
    _check_item_permission(request, item)

    session = item.session
    map_obj = session.active_map

    # Aktuellen Position der Quell-Figur holen
    from_pos = None
    if map_obj:
        from_pos = (
            CharacterPosition.objects
            .filter(character=item.character, session=session, map=map_obj)
            .order_by('-timestamp').first()
        )

    # Mögliche Ziel-Figuren: andere Teilnehmer (nicht die Quell-Figur, nicht entfernt)
    from sessions.models import SessionParticipant
    other_participants = SessionParticipant.objects.filter(
        session=session, is_removed=False, is_confirmed=True,
    ).exclude(character=item.character).select_related('character')

    # Nähe prüfen (≤ 2%)
    nearby = []
    for p in other_participants:
        if map_obj and from_pos:
            pos = (
                CharacterPosition.objects
                .filter(character=p.character, session=session, map=map_obj)
                .order_by('-timestamp').first()
            )
            if pos:
                dx = from_pos.x_pos - pos.x_pos
                dy = from_pos.y_pos - pos.y_pos
                if (dx * dx + dy * dy) ** 0.5 <= 0.02:
                    nearby.append(p.character)

    return render(request, 'inventory/item_transfer_form.html', {
        'item': item,
        'nearby_characters': nearby,
    })


@login_required
@require_POST
def item_transfer(request, item_pk):
    """Übergibt ein Item an eine andere Figur."""
    item = get_object_or_404(
        InventoryItem.objects.select_related('character', 'session', 'session__active_map'),
        pk=item_pk,
    )
    _check_item_permission(request, item)

    target_char_pk = request.POST.get('target_character')
    target_char = get_object_or_404(Character, pk=target_char_pk)

    # Erneute Nähe-Prüfung (serverseitig)
    session = item.session
    map_obj = session.active_map
    if map_obj:
        from_pos = (
            CharacterPosition.objects
            .filter(character=item.character, session=session, map=map_obj)
            .order_by('-timestamp').first()
        )
        to_pos = (
            CharacterPosition.objects
            .filter(character=target_char, session=session, map=map_obj)
            .order_by('-timestamp').first()
        )
        if from_pos and to_pos:
            dx = from_pos.x_pos - to_pos.x_pos
            dy = from_pos.y_pos - to_pos.y_pos
            if (dx * dx + dy * dy) ** 0.5 > 0.02:
                return render(request, 'inventory/item_transfer_form.html', {
                    'item': item,
                    'error': 'Die Figuren sind nicht nah genug beieinander (max. 2%).',
                    'nearby_characters': [],
                }, status=422)

    item.character = target_char
    item.save(update_fields=['character'])

    response = HttpResponse(status=200)
    response['HX-Trigger'] = 'inventoryUpdated'
    return response
