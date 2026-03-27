import json
from datetime import timedelta

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from characters.models import Character
from maps.models import Gate, Map, MapSet
from maps.views import _get_visible_elements

# Farb-Palette für automatische Figuren-Farb-Zuweisung in Sessions
_SESSION_COLORS = [
    '#ef4444',  # Rot
    '#3b82f6',  # Blau
    '#22c55e',  # Grün
    '#f59e0b',  # Gelb
    '#a855f7',  # Lila
    '#14b8a6',  # Türkis
    '#f97316',  # Orange
    '#ec4899',  # Pink
    '#06b6d4',  # Cyan
    '#84cc16',  # Hellgrün
]


def _assign_session_color(session, character):
    """Weist der Figur eine in dieser Session noch nicht verwendete Farbe zu."""
    used_colors = set(
        SessionParticipant.objects
        .filter(session=session, is_removed=False)
        .exclude(character=character)
        .values_list('character__color', flat=True)
    )
    for color in _SESSION_COLORS:
        if color not in used_colors:
            character.color = color
            character.save(update_fields=['color'])
            return
    # Fallback: erste Farbe der Palette wenn alle belegt
    character.color = _SESSION_COLORS[0]
    character.save(update_fields=['color'])

from .forms import (
    ParticipantRoleForm,
    SessionCreateForm,
    SessionJoinCharacterForm,
    SessionJoinPasswordForm,
)
from .models import CharacterPosition, GameSession, SessionParticipant


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _check_gamemaster(request, session):
    """Wirft PermissionDenied, wenn der User kein Spielleiter dieser Session ist."""
    is_gm = SessionParticipant.objects.filter(
        session=session, user=request.user, role='gamemaster',
        is_removed=False, is_confirmed=True,
    ).exists()
    if not is_gm and not request.user.is_admin:
        raise PermissionDenied


def _get_participant_or_403(request, session):
    """Gibt den SessionParticipant zurück oder wirft PermissionDenied."""
    try:
        return SessionParticipant.objects.select_related('character').get(
            session=session, user=request.user, is_removed=False, is_confirmed=True,
        )
    except SessionParticipant.DoesNotExist:
        raise PermissionDenied


def _build_map_data(map_obj, request):
    """Erstellt das map_data-Dict für das Session-Template (wie map_view)."""
    return {
        'id': map_obj.pk,
        'title': map_obj.title,
        'type': map_obj.map_set.map_type,
        'image_url': request.build_absolute_uri(map_obj.image.url) if map_obj.image else None,
        'image_width': map_obj.image_width or 1000,
        'image_height': map_obj.image_height or 1000,
        'tiles_url': map_obj.tiles_url,
        'tiles_bounds': map_obj.tiles_bounds,
        'zoom_min': map_obj.zoom_min,
        'zoom_max': map_obj.zoom_max,
        'center_x': map_obj.center_x,
        'center_y': map_obj.center_y,
    }


def _build_characters_data(session, map_obj, request):
    """
    Erstellt die characters_data-Liste mit aktuellen Positionen aller Teilnehmer.
    """
    participants = (
        SessionParticipant.objects
        .filter(session=session, is_removed=False)
        .select_related('character', 'character__owner', 'user')
    )
    result = []
    for p in participants:
        char = p.character
        # Letzte Position auf der aktuellen Karte
        pos_current = (
            CharacterPosition.objects
            .filter(character=char, session=session, map=map_obj)
            .order_by('-timestamp').first()
        )
        # Letzte Position auf irgendeiner Karte (für Sidebar-Info)
        pos_any = (
            CharacterPosition.objects
            .filter(character=char, session=session)
            .select_related('map')
            .order_by('-timestamp').first()
        )
        result.append({
            'id': char.pk,
            'participant_id': p.pk,
            'name': char.name,
            'color': char.color,
            'avatar_url': (
                request.build_absolute_uri(char.avatar_image.url)
                if char.avatar_image else None
            ),
            'role': p.role,
            'is_eliminated': p.is_eliminated,
            'on_current_map': pos_current is not None,
            'x_pos': pos_current.x_pos if pos_current else map_obj.center_x,
            'y_pos': pos_current.y_pos if pos_current else map_obj.center_y,
            'current_map_title': pos_any.map.title if pos_any else None,
            'current_map_id': pos_any.map_id if pos_any else None,
        })
    return result


def _broadcast(group_name, message):
    """Sendet ein Channel-Layer-Event (sync Wrapper)."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name, message)


# ---------------------------------------------------------------------------
# Session-Liste
# ---------------------------------------------------------------------------

@login_required
def session_list(request):
    participated = (
        SessionParticipant.objects
        .filter(user=request.user, is_removed=False)
        .select_related('session', 'session__initiator')
        .order_by('-session__created_at')
    )
    return render(request, 'sessions/session_list.html', {'participated': participated})


# ---------------------------------------------------------------------------
# Session anlegen
# ---------------------------------------------------------------------------

@login_required
def session_create(request):
    form = SessionCreateForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data

        # Startkarte bestimmen
        map_set = d.get('map_set')
        initial_map = None
        if map_set:
            initial_map = map_set.maps.filter(is_main=True).first() or map_set.maps.first()

        session = GameSession.objects.create(
            initiator=request.user,
            title=d['title'],
            password=make_password(d['password_plain']),
            status='waiting',
            active_map=initial_map,
        )

        char = d['character']
        char.current_session = session
        char.save(update_fields=['current_session'])

        SessionParticipant.objects.create(
            session=session,
            user=request.user,
            character=char,
            role=d['role'],
            is_confirmed=True,
        )

        messages.success(request, f'Session „{session.title}" erstellt.')
        return redirect('game_sessions:session_lobby', pk=session.pk)

    return render(request, 'sessions/session_create.html', {'form': form})


# ---------------------------------------------------------------------------
# Lobby (Warteraum, status='waiting')
# ---------------------------------------------------------------------------

@login_required
def session_lobby(request, pk):
    session = get_object_or_404(GameSession, pk=pk)

    # Nur Teilnehmer oder Initiatoren können die Lobby sehen
    try:
        my_participant = SessionParticipant.objects.get(
            session=session, user=request.user, is_removed=False,
        )
    except SessionParticipant.DoesNotExist:
        raise PermissionDenied

    if session.status == 'running':
        return redirect('game_sessions:session_view', pk=session.pk)
    if session.status == 'finished':
        return redirect('game_sessions:session_list')

    is_gamemaster = my_participant.role == 'gamemaster'
    invite_url = request.build_absolute_uri(
        f'/sessions/join/{session.invite_token}/'
    )
    participants = SessionParticipant.objects.filter(
        session=session, is_removed=False,
    ).select_related('user', 'character')

    return render(request, 'sessions/session_lobby.html', {
        'session': session,
        'my_participant': my_participant,
        'participants': participants,
        'is_gamemaster': is_gamemaster,
        'invite_url': invite_url,
    })


@login_required
def lobby_participants(request, pk):
    """HTMX-Partial: aktuelle Teilnehmerliste für die Lobby (Polling)."""
    session = get_object_or_404(GameSession, pk=pk)
    try:
        my_participant = SessionParticipant.objects.get(
            session=session, user=request.user, is_removed=False,
        )
    except SessionParticipant.DoesNotExist:
        raise PermissionDenied
    is_gamemaster = my_participant.role == 'gamemaster'
    participants = SessionParticipant.objects.filter(
        session=session, is_removed=False,
    ).select_related('user', 'character')
    return render(request, 'sessions/partials/lobby_participants.html', {
        'session': session,
        'participants': participants,
        'is_gamemaster': is_gamemaster,
    })


# ---------------------------------------------------------------------------
# Session beitreten
# ---------------------------------------------------------------------------

@login_required
def session_join(request, invite_token):
    session = get_object_or_404(GameSession, invite_token=invite_token)

    # Bereits Teilnehmer?
    existing = SessionParticipant.objects.filter(
        session=session, user=request.user, is_removed=False,
    ).first()
    if existing:
        if existing.is_confirmed:
            return redirect('game_sessions:session_lobby', pk=session.pk)
        return redirect('game_sessions:session_join_waiting', pk=session.pk)

    if session.status != 'waiting':
        messages.error(request, 'Diese Session nimmt keine neuen Teilnehmer mehr an.')
        return redirect('game_sessions:session_list')

    pw_form = SessionJoinPasswordForm(session, request.POST or None, prefix='pw')
    char_form = SessionJoinCharacterForm(request.user, request.POST or None, prefix='ch')

    if request.method == 'POST' and pw_form.is_valid() and char_form.is_valid():
        char = char_form.cleaned_data['character']
        char.current_session = session
        char.save(update_fields=['current_session'])

        SessionParticipant.objects.create(
            session=session,
            user=request.user,
            character=char,
            role='player',
            is_confirmed=False,
        )
        messages.success(request, 'Beitrittsanfrage gesendet. Warte auf Bestätigung.')
        return redirect('game_sessions:session_join_waiting', pk=session.pk)

    return render(request, 'sessions/session_join.html', {
        'session': session,
        'pw_form': pw_form,
        'char_form': char_form,
    })


@login_required
def session_join_waiting(request, pk):
    """Warteseite nach dem Beitrittsantrag."""
    session = get_object_or_404(GameSession, pk=pk)
    try:
        participant = SessionParticipant.objects.get(
            session=session, user=request.user, is_removed=False,
        )
    except SessionParticipant.DoesNotExist:
        return redirect('game_sessions:session_list')

    if participant.is_confirmed:
        if session.status == 'running':
            return redirect('game_sessions:session_view', pk=session.pk)
        return redirect('game_sessions:session_lobby', pk=session.pk)

    return render(request, 'sessions/session_join_waiting.html', {
        'session': session,
        'participant': participant,
    })


@login_required
def join_status_check(request, pk):
    """HTMX-Partial: prüft ob der Beitritt bestätigt wurde (Polling)."""
    session = get_object_or_404(GameSession, pk=pk)
    try:
        participant = SessionParticipant.objects.get(
            session=session, user=request.user, is_removed=False,
        )
    except SessionParticipant.DoesNotExist:
        return HttpResponse(
            '<p class="text-red-400">Zugang verweigert.</p>',
        )
    if participant.is_confirmed:
        target_url = (
            f'/sessions/{session.pk}/view/'
            if session.status == 'running'
            else f'/sessions/{session.pk}/lobby/'
        )
        return HttpResponse(
            f'<script>window.location.href="{target_url}";</script>',
        )
    return render(request, 'sessions/partials/join_status_check.html', {
        'session': session,
    })


# ---------------------------------------------------------------------------
# Teilnehmer-Management (Lobby, nur Spielleiter)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def participant_confirm(request, participant_pk):
    p = get_object_or_404(SessionParticipant.objects.select_related('session'), pk=participant_pk)
    _check_gamemaster(request, p.session)
    role = request.POST.get('role', 'player')
    if role not in dict(SessionParticipant.ROLE_CHOICES):
        role = 'player'
    p.is_confirmed = True
    p.role = role
    p.save(update_fields=['is_confirmed', 'role'])
    return redirect('game_sessions:session_lobby', pk=p.session_id)


@login_required
@require_POST
def participant_reject(request, participant_pk):
    p = get_object_or_404(SessionParticipant.objects.select_related('session', 'character'), pk=participant_pk)
    _check_gamemaster(request, p.session)
    # Figur freigeben
    Character.objects.filter(pk=p.character_id).update(current_session=None)
    session_pk = p.session_id
    p.delete()
    return redirect('game_sessions:session_lobby', pk=session_pk)


# ---------------------------------------------------------------------------
# Session starten / beenden
# ---------------------------------------------------------------------------

@login_required
@require_POST
def session_start(request, pk):
    session = get_object_or_404(GameSession, pk=pk)
    _check_gamemaster(request, session)
    if session.status != 'waiting':
        messages.error(request, 'Session ist nicht im Wartezustand.')
        return redirect('game_sessions:session_lobby', pk=session.pk)
    confirmed_count = SessionParticipant.objects.filter(
        session=session, is_confirmed=True, is_removed=False,
    ).count()
    if confirmed_count < 1:
        messages.error(request, 'Mindestens ein Teilnehmer muss bestätigt sein.')
        return redirect('game_sessions:session_lobby', pk=session.pk)
    session.status = 'running'
    session.save(update_fields=['status', 'last_activity'])
    messages.success(request, 'Session gestartet!')
    return redirect('game_sessions:session_view', pk=session.pk)


@login_required
@require_POST
def session_end(request, pk):
    session = get_object_or_404(GameSession, pk=pk)
    _check_gamemaster(request, session)
    _end_session(session)
    _broadcast(f'session_{session.pk}', {'type': 'session_ended'})
    messages.success(request, 'Session beendet.')
    return redirect('game_sessions:session_list')


def _end_session(session):
    """Interne Hilfsfunktion: Session beenden und alle Figuren freigeben."""
    session.status = 'finished'
    session.save(update_fields=['status'])
    # Alle current_session zurücksetzen
    char_ids = SessionParticipant.objects.filter(
        session=session,
    ).values_list('character_id', flat=True)
    Character.objects.filter(pk__in=char_ids).update(current_session=None)


# ---------------------------------------------------------------------------
# Session-Ansicht (status='running')
# ---------------------------------------------------------------------------

@login_required
def session_view(request, pk):
    session = get_object_or_404(
        GameSession.objects.select_related('active_map', 'active_map__map_set'),
        pk=pk,
    )

    # Stale-Check: > 30 Tage Inaktivität
    is_stale = (
        session.status == 'running'
        and session.last_activity < timezone.now() - timedelta(days=30)
    )

    if session.status == 'waiting':
        return redirect('game_sessions:session_lobby', pk=session.pk)
    if session.status == 'finished':
        messages.info(request, 'Diese Session ist beendet.')
        return redirect('game_sessions:session_list')

    my_participant = _get_participant_or_403(request, session)
    is_gamemaster = my_participant.role == 'gamemaster'

    map_obj = session.active_map
    if not map_obj:
        # Kein active_map → Hinweis anzeigen
        return render(request, 'sessions/session_no_map.html', {
            'session': session,
            'is_gamemaster': is_gamemaster,
            'is_stale': is_stale,
        })

    map_data = _build_map_data(map_obj, request)
    gates = list(map_obj.gates.select_related('target_map').values(
        'id', 'icon_type', 'label', 'x_pos', 'y_pos', 'target_map_id',
    ))
    elements = _get_visible_elements(map_obj, request.user, is_gamemaster)
    characters_data = _build_characters_data(session, map_obj, request)

    session_data = {
        'id': session.pk,
        'title': session.title,
        'status': session.status,
        'active_map_id': map_obj.pk,
    }

    return render(request, 'sessions/session_view.html', {
        'session': session,
        'map': map_obj,
        'is_gamemaster': is_gamemaster,
        'is_stale': is_stale,
        'my_participant': my_participant,
        'characters': characters_data,   # für Template-Iteration (Sidebar)
        'session_data_json': json.dumps(session_data),
        'map_data_json': json.dumps(map_data),
        'gates_json': json.dumps(gates),
        'elements_json': json.dumps(elements),
        'characters_json': json.dumps(characters_data),
    })


# ---------------------------------------------------------------------------
# Teilnehmer-Aktionen während der Session (Spielleiter)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def participant_eliminate(request, participant_pk):
    p = get_object_or_404(SessionParticipant.objects.select_related('session'), pk=participant_pk)
    _check_gamemaster(request, p.session)
    p.is_eliminated = True
    p.save(update_fields=['is_eliminated'])
    _broadcast(f'session_{p.session_id}', {
        'type': 'figure_eliminated',
        'character_id': p.character_id,
    })
    return redirect('game_sessions:session_view', pk=p.session_id)


@login_required
@require_POST
def participant_remove(request, participant_pk):
    p = get_object_or_404(
        SessionParticipant.objects.select_related('session', 'character'), pk=participant_pk,
    )
    _check_gamemaster(request, p.session)
    p.is_removed = True
    p.save(update_fields=['is_removed'])
    Character.objects.filter(pk=p.character_id).update(current_session=None)
    return redirect('game_sessions:session_view', pk=p.session_id)


# ---------------------------------------------------------------------------
# Karte wechseln (Spielleiter)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def session_change_map(request, pk):
    session = get_object_or_404(GameSession, pk=pk)
    _check_gamemaster(request, session)
    map_pk = request.POST.get('map_id')
    new_map = get_object_or_404(Map, pk=map_pk)
    # Karte muss zum gleichen MapSet gehören
    if session.active_map and session.active_map.map_set_id != new_map.map_set_id:
        messages.error(request, 'Karte gehört nicht zum gleichen Karten-Set.')
        return redirect('game_sessions:session_view', pk=session.pk)
    old_map_id = session.active_map_id
    session.active_map = new_map
    session.save(update_fields=['active_map', 'last_activity'])
    _broadcast(f'session_{session.pk}', {
        'type': 'figure_joined_map',
        'character_id': None,
        'old_map_id': old_map_id,
        'new_map_id': new_map.pk,
        'x_pos': new_map.center_x,
        'y_pos': new_map.center_y,
    })
    return redirect('game_sessions:session_view', pk=session.pk)


# ---------------------------------------------------------------------------
# Positions-Pfad abrufen (AJAX, für JS)
# ---------------------------------------------------------------------------

@login_required
def character_path(request, session_pk, character_pk):
    session = get_object_or_404(GameSession, pk=session_pk)
    _get_participant_or_403(request, session)
    map_obj = session.active_map
    if not map_obj:
        return JsonResponse({'positions': []})
    positions = list(
        CharacterPosition.objects
        .filter(character_id=character_pk, session=session, map=map_obj)
        .order_by('timestamp')
        .values('x_pos', 'y_pos')
    )
    return JsonResponse({'positions': positions})


# ---------------------------------------------------------------------------
# Quest-Sidebar (HTMX-Partial)
# ---------------------------------------------------------------------------

@login_required
def quest_sidebar(request, session_pk):
    session = get_object_or_404(
        GameSession.objects.select_related('active_map__map_set'), pk=session_pk,
    )
    my_participant = _get_participant_or_403(request, session)
    is_gamemaster = my_participant.role == 'gamemaster'

    from quests.models import CharacterQuest
    character_quests = (
        CharacterQuest.objects
        .filter(session=session)
        .select_related('character', 'quest', 'current_step')
        .order_by('character__name', 'quest__title')
    )

    return render(request, 'sessions/partials/quest_sidebar.html', {
        'session': session,
        'character_quests': character_quests,
        'is_gamemaster': is_gamemaster,
    })


# ---------------------------------------------------------------------------
# Inventar-Sidebar (HTMX-Partial)
# ---------------------------------------------------------------------------

@login_required
def inventory_sidebar(request, session_pk):
    session = get_object_or_404(GameSession, pk=session_pk)
    my_participant = _get_participant_or_403(request, session)
    is_gamemaster = my_participant.role == 'gamemaster'

    from inventory.models import InventoryItem
    items = (
        InventoryItem.objects
        .filter(session=session)
        .select_related('character', 'map_element', 'map_element__item')
        .order_by('character__name', '-picked_up_at')
    )

    return render(request, 'sessions/partials/inventory_sidebar.html', {
        'session': session,
        'items': items,
        'is_gamemaster': is_gamemaster,
        'my_character': my_participant.character,
    })


# ---------------------------------------------------------------------------
# Quest zuweisen (Spielleiter)
# ---------------------------------------------------------------------------

@login_required
def assign_quest_form(request, session_pk):
    """HTMX-Partial GET: Formular zum Zuweisen einer Quest an Figuren."""
    session = get_object_or_404(
        GameSession.objects.select_related('active_map__map_set'), pk=session_pk,
    )
    _check_gamemaster(request, session)

    from quests.models import Quest
    map_set = session.active_map.map_set if session.active_map else None
    if map_set:
        quests = Quest.objects.filter(map_set=map_set).order_by('title')
    else:
        quests = Quest.objects.none()

    participants = (
        SessionParticipant.objects
        .filter(session=session, is_removed=False, is_confirmed=True)
        .select_related('character')
    )

    return render(request, 'sessions/partials/assign_quest_form.html', {
        'session': session,
        'quests': quests,
        'participants': participants,
    })


@login_required
@require_POST
def assign_quest(request, session_pk):
    """Quest an ausgewählte Figuren zuweisen."""
    session = get_object_or_404(
        GameSession.objects.select_related('active_map__map_set'), pk=session_pk,
    )
    _check_gamemaster(request, session)

    from quests.models import Quest, CharacterQuest
    quest_pk = request.POST.get('quest_id')
    character_pks = request.POST.getlist('character_ids')

    quest = get_object_or_404(Quest, pk=quest_pk)
    first_step = quest.steps.order_by('order').first()

    assigned = 0
    for char_pk in character_pks:
        char = get_object_or_404(Character, pk=char_pk)
        _, created = CharacterQuest.objects.get_or_create(
            character=char,
            quest=quest,
            session=session,
            defaults={'status': 'active', 'current_step': first_step},
        )
        if created:
            assigned += 1

    response = render(request, 'sessions/partials/assign_quest_success.html', {
        'quest': quest,
        'assigned': assigned,
        'session': session,
    })
    response['HX-Trigger'] = 'questUpdated'
    return response


# ---------------------------------------------------------------------------
# CharacterQuest-Fortschritt (Spielleiter)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def character_quest_next_step(request, cq_pk):
    """Nächsten Schritt einer CharacterQuest aktivieren."""
    from quests.models import CharacterQuest
    cq = get_object_or_404(CharacterQuest.objects.select_related('quest', 'current_step', 'session'), pk=cq_pk)
    _check_gamemaster(request, cq.session)

    if cq.current_step:
        next_step = (
            cq.quest.steps
            .filter(order__gt=cq.current_step.order)
            .order_by('order')
            .first()
        )
        if next_step:
            cq.current_step = next_step
            cq.save(update_fields=['current_step'])
        else:
            # Letzter Schritt → Quest abschließen
            cq.status = 'completed'
            cq.save(update_fields=['status'])

    response = HttpResponse(status=200)
    response['HX-Trigger'] = 'questUpdated'
    return response


@login_required
@require_POST
def character_quest_complete(request, cq_pk):
    """CharacterQuest als abgeschlossen markieren."""
    from quests.models import CharacterQuest
    cq = get_object_or_404(CharacterQuest.objects.select_related('session'), pk=cq_pk)
    _check_gamemaster(request, cq.session)
    cq.status = 'completed'
    cq.save(update_fields=['status'])
    response = HttpResponse(status=200)
    response['HX-Trigger'] = 'questUpdated'
    return response


@login_required
@require_POST
def character_quest_fail(request, cq_pk):
    """CharacterQuest als fehlgeschlagen markieren."""
    from quests.models import CharacterQuest
    cq = get_object_or_404(CharacterQuest.objects.select_related('session'), pk=cq_pk)
    _check_gamemaster(request, cq.session)
    cq.status = 'failed'
    cq.save(update_fields=['status'])
    response = HttpResponse(status=200)
    response['HX-Trigger'] = 'questUpdated'
    return response
