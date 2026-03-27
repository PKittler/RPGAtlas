import json
import os
import shutil
import sqlite3

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from advertising.models import AdIcon
from .forms import (
    GateForm, MapAddImageForm, MapAddTilesForm, MapSetCreateForm, MapSetEditForm,
    NPCForm, ItemForm, TriggerForm,
)
from .models import ElementCondition, Gate, Map, MapElement, MapSet


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _check_mapset_owner(request, mapset):
    """Wirft PermissionDenied, wenn der User kein Eigentümer und kein Admin ist."""
    if mapset.owner != request.user and not request.user.is_admin:
        raise PermissionDenied


def _extract_mbtiles_bounds(file_path):
    """Liest die geografischen Bounds aus der MBTiles-Metadaten-Tabelle."""
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE name='bounds'")
        row = cursor.fetchone()
        conn.close()
        if row:
            parts = [float(x.strip()) for x in row[0].split(',')]
            return {'west': parts[0], 'south': parts[1], 'east': parts[2], 'north': parts[3]}
    except Exception:
        pass
    return {'west': -180.0, 'south': -85.0, 'east': 180.0, 'north': 85.0}


def _copy_mbtiles_to_tileserver(src_path, filename):
    """Kopiert die MBTiles-Datei in das TileServer-GL-Volume."""
    tileserver_dir = '/tileserver_data'
    if os.path.isdir(tileserver_dir):
        dest = os.path.join(tileserver_dir, filename)
        shutil.copy2(src_path, dest)


def _get_user_active_session(user, map_obj):
    """Gibt die laufende Session zurück, in der der User auf dieser Karte aktiv ist."""
    from sessions.models import SessionParticipant
    try:
        participant = SessionParticipant.objects.select_related('session').get(
            user=user,
            session__status='running',
            session__active_map=map_obj,
            is_removed=False,
        )
        return participant.session
    except SessionParticipant.DoesNotExist:
        return None


def _check_element_conditions(element, user, session):
    """Prüft, ob alle Quest-Bedingungen eines Elements erfüllt sind."""
    from sessions.models import SessionParticipant
    from quests.models import CharacterQuest
    try:
        participant = session.participants.get(user=user, is_removed=False)
    except Exception:
        return False
    for cond in element.conditions.all():
        if cond.required_quest and cond.condition_type == 'quest_completed':
            fulfilled = CharacterQuest.objects.filter(
                character=participant.character,
                quest=cond.required_quest,
                status='completed',
            ).exists()
            if not fulfilled:
                return False
    return True


def _get_visible_elements(map_obj, user, is_owner):
    """Gibt die für den User sichtbaren MapElements als Liste von dicts zurück."""
    elements = map_obj.elements.prefetch_related('conditions')
    if is_owner:
        return [el.to_dict() for el in elements]
    active_session = _get_user_active_session(user, map_obj)
    result = []
    for el in elements:
        if not el.is_conditional:
            result.append(el.to_dict())
        elif active_session and _check_element_conditions(el, user, active_session):
            result.append(el.to_dict())
    return result


def _get_visible_ads(map_obj, user):
    """Gibt die für diesen User sichtbaren AdIcons einer Karte zurück."""
    if not map_obj.map_set.allow_ads:
        return []
    if user.is_authenticated and user.hide_ads:
        return []
    icons = AdIcon.objects.filter(
        map=map_obj,
        is_active=True,
        campaign__is_active=True,
    ).select_related('campaign')
    return [ad for ad in icons if ad.is_visible()]


# ---------------------------------------------------------------------------
# MapSet-Views
# ---------------------------------------------------------------------------

@login_required
def mapset_list(request):
    if request.user.is_admin:
        mapsets = MapSet.objects.all().select_related('owner').order_by('-created_at')
    else:
        mapsets = MapSet.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'maps/mapset_list.html', {'mapsets': mapsets})


@login_required
def mapset_create(request):
    form = MapSetCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mapset = form.save(commit=False)
        mapset.owner = request.user
        mapset.save()
        messages.success(request, f'Karten-Set „{mapset.title}" erstellt.')
        return redirect('maps:mapset_detail', pk=mapset.pk)
    return render(request, 'maps/mapset_create.html', {'form': form})


@login_required
def mapset_detail(request, pk):
    mapset = get_object_or_404(MapSet, pk=pk)
    _check_mapset_owner(request, mapset)
    maps = mapset.maps.order_by('-is_main', 'title')
    return render(request, 'maps/mapset_detail.html', {
        'mapset': mapset,
        'maps': maps,
        'is_owner': mapset.owner == request.user or request.user.is_admin,
    })


@login_required
def mapset_edit(request, pk):
    mapset = get_object_or_404(MapSet, pk=pk)
    _check_mapset_owner(request, mapset)
    form = MapSetEditForm(request.POST or None, instance=mapset)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Karten-Set aktualisiert.')
        return redirect('maps:mapset_detail', pk=mapset.pk)
    return render(request, 'maps/mapset_edit.html', {
        'form': form,
        'mapset': mapset,
    })


@login_required
def mapset_delete(request, pk):
    mapset = get_object_or_404(MapSet, pk=pk)
    _check_mapset_owner(request, mapset)
    if request.method == 'POST':
        title = mapset.title
        mapset.delete()
        messages.success(request, f'Karten-Set „{title}" gelöscht.')
        return redirect('maps:mapset_list')
    return render(request, 'maps/mapset_delete.html', {'mapset': mapset})


# ---------------------------------------------------------------------------
# Karten-Views
# ---------------------------------------------------------------------------

@login_required
def map_add(request, mapset_pk):
    mapset = get_object_or_404(MapSet, pk=mapset_pk)
    _check_mapset_owner(request, mapset)

    FormClass = MapAddImageForm if mapset.map_type == 'image' else MapAddTilesForm

    form = FormClass(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        map_obj = form.save(commit=False)
        map_obj.map_set = mapset

        if mapset.map_type == 'image':
            # Bilddimensionen mit Pillow auslesen
            from PIL import Image as PILImage
            uploaded = form.cleaned_data.get('image')
            if uploaded:
                uploaded.seek(0)
                img = PILImage.open(uploaded)
                map_obj.image_width = img.width
                map_obj.image_height = img.height

        elif mapset.map_type == 'tiles':
            map_obj.save()  # Datei erst speichern, dann Pfad nutzen
            saved_path = map_obj.tiles_file.path
            filename = os.path.basename(saved_path)
            source_id = os.path.splitext(filename)[0]

            _copy_mbtiles_to_tileserver(saved_path, filename)

            # Externe URL für Leaflet (nginx-Proxy: /tiles/ → tileserver:8080/)
            map_obj.tiles_url = f'/tiles/data/{source_id}/{{z}}/{{x}}/{{y}}.png'
            map_obj.tiles_bounds = _extract_mbtiles_bounds(saved_path)

        # is_main: nur eine Karte darf Hauptkarte sein
        if form.cleaned_data.get('is_main'):
            mapset.maps.exclude(pk=map_obj.pk).update(is_main=False)

        if mapset.map_type != 'tiles':
            map_obj.save()
        else:
            map_obj.save(update_fields=['tiles_url', 'tiles_bounds', 'is_main'])

        messages.success(request, f'Karte „{map_obj.title}" hinzugefügt.')
        return redirect('maps:mapset_detail', pk=mapset.pk)

    return render(request, 'maps/map_add.html', {
        'form': form,
        'mapset': mapset,
    })


@login_required
def map_delete(request, pk):
    map_obj = get_object_or_404(Map, pk=pk)
    _check_mapset_owner(request, map_obj.map_set)
    mapset = map_obj.map_set
    if request.method == 'POST':
        title = map_obj.title
        map_obj.delete()
        messages.success(request, f'Karte „{title}" gelöscht.')
        return redirect('maps:mapset_detail', pk=mapset.pk)
    return render(request, 'maps/map_delete.html', {
        'map': map_obj,
        'mapset': mapset,
    })


# ---------------------------------------------------------------------------
# Karten-Ansicht (Leaflet)
# ---------------------------------------------------------------------------

@login_required
def map_view(request, pk):
    map_obj = get_object_or_404(
        Map.objects.select_related('map_set', 'map_set__owner'), pk=pk
    )

    # Sichtbarkeit: Eigentümer, Admin oder jeder eingeloggte User (Sessions kommen in Phase 4)
    # Für Phase 2: Nur Eigentümer und Admin dürfen die Karte sehen
    _check_mapset_owner(request, map_obj.map_set)

    gates = list(map_obj.gates.select_related('target_map').values(
        'id', 'icon_type', 'label', 'x_pos', 'y_pos', 'target_map_id',
    ))

    ads = [ad.to_dict() for ad in _get_visible_ads(map_obj, request.user)]

    map_data = {
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

    is_owner = map_obj.map_set.owner == request.user or request.user.is_admin
    elements = _get_visible_elements(map_obj, request.user, is_owner)

    return render(request, 'maps/map_view.html', {
        'map': map_obj,
        'mapset': map_obj.map_set,
        'map_data_json': json.dumps(map_data),
        'gates_json': json.dumps(gates),
        'ads_json': json.dumps(ads),
        'elements_json': json.dumps(elements),
        'is_owner': is_owner,
    })


# ---------------------------------------------------------------------------
# Gate-Views (HTMX)
# ---------------------------------------------------------------------------

@login_required
def gate_form(request, map_pk):
    """Gibt das Gate-Formular als HTMX-Partial zurück."""
    map_obj = get_object_or_404(Map, pk=map_pk)
    _check_mapset_owner(request, map_obj.map_set)

    x_pos = request.GET.get('x', '0.5')
    y_pos = request.GET.get('y', '0.5')
    form = GateForm(map_set=map_obj.map_set)

    return render(request, 'maps/partials/gate_form.html', {
        'form': form,
        'map': map_obj,
        'x_pos': x_pos,
        'y_pos': y_pos,
    })


@login_required
@require_POST
def gate_add(request, map_pk):
    """Erstellt ein Gate, gibt das Marker-Partial zurück (HTMX-Swap out-of-band)."""
    map_obj = get_object_or_404(Map, pk=map_pk)
    _check_mapset_owner(request, map_obj.map_set)

    form = GateForm(map_set=map_obj.map_set, data=request.POST)
    if form.is_valid():
        gate = form.save(commit=False)
        gate.source_map = map_obj
        gate.x_pos = float(request.POST.get('x_pos', 0.5))
        gate.y_pos = float(request.POST.get('y_pos', 0.5))
        gate.save()

        # HX-Trigger: JS-Event auslösen, damit Leaflet den Marker hinzufügt
        gate_data = json.dumps(gate.to_dict())
        response = render(request, 'maps/partials/gate_form_success.html', {
            'gate': gate,
        })
        response['HX-Trigger'] = json.dumps({'gateAdded': gate.to_dict()})
        return response

    return render(request, 'maps/partials/gate_form.html', {
        'form': form,
        'map': map_obj,
        'x_pos': request.POST.get('x_pos', '0.5'),
        'y_pos': request.POST.get('y_pos', '0.5'),
    }, status=422)


@login_required
@require_POST
def gate_delete(request, gate_pk):
    """Löscht ein Gate und sendet HX-Trigger, damit Leaflet den Marker entfernt."""
    gate = get_object_or_404(Gate, pk=gate_pk)
    _check_mapset_owner(request, gate.source_map.map_set)

    gate_id = gate.pk
    gate.delete()

    from django.http import HttpResponse
    response = HttpResponse(status=200)
    response['HX-Trigger'] = json.dumps({'gateDeleted': {'id': gate_id}})
    return response


# ---------------------------------------------------------------------------
# Werbe-Icon-Views (HTMX)
# ---------------------------------------------------------------------------

@login_required
def ad_modal(request, ad_pk):
    """Gibt das Ad-Modal als HTMX-Partial zurück."""
    ad = get_object_or_404(AdIcon, pk=ad_pk)
    return render(request, 'maps/partials/ad_modal.html', {'ad': ad})


@login_required
@require_POST
def ad_click(request, ad_pk):
    """Erhöht den click_count eines AdIcons um 1."""
    ad = get_object_or_404(AdIcon, pk=ad_pk)
    AdIcon.objects.filter(pk=ad_pk).update(click_count=ad.click_count + 1)
    from django.http import HttpResponse
    return HttpResponse(status=200)


# ---------------------------------------------------------------------------
# Karten-Element-Views (HTMX)
# ---------------------------------------------------------------------------

@login_required
def element_type_select(request, map_pk):
    """Gibt die Typ-Auswahl als HTMX-Partial zurück (Schritt 1)."""
    map_obj = get_object_or_404(Map, pk=map_pk)
    _check_mapset_owner(request, map_obj.map_set)
    x_pos = request.GET.get('x', '0.5')
    y_pos = request.GET.get('y', '0.5')
    return render(request, 'maps/partials/element_type_select.html', {
        'map': map_obj,
        'x_pos': x_pos,
        'y_pos': y_pos,
    })


@login_required
def element_form(request, map_pk, element_type):
    """Gibt das typspezifische Formular als HTMX-Partial zurück (Schritt 2)."""
    map_obj = get_object_or_404(Map, pk=map_pk)
    _check_mapset_owner(request, map_obj.map_set)
    if element_type not in ('npc', 'item', 'trigger'):
        from django.http import HttpResponse
        return HttpResponse(status=400)

    x_pos = request.GET.get('x', '0.5')
    y_pos = request.GET.get('y', '0.5')
    form_classes = {'npc': NPCForm, 'item': ItemForm, 'trigger': TriggerForm}
    form = form_classes[element_type]()
    quests = map_obj.map_set.quests.all()

    return render(request, f'maps/partials/element_form_{element_type}.html', {
        'form': form,
        'map': map_obj,
        'x_pos': x_pos,
        'y_pos': y_pos,
        'quests': quests,
        'element_type': element_type,
    })


@login_required
@require_POST
def element_add(request, map_pk):
    """Erstellt ein MapElement (inkl. Typ-spezifischem Modell und Bedingungen)."""
    map_obj = get_object_or_404(Map, pk=map_pk)
    _check_mapset_owner(request, map_obj.map_set)

    element_type = request.POST.get('element_type', '')
    form_classes = {'npc': NPCForm, 'item': ItemForm, 'trigger': TriggerForm}
    FormClass = form_classes.get(element_type)
    if not FormClass:
        from django.http import HttpResponse
        return HttpResponse(status=400)

    form = FormClass(request.POST, request.FILES)
    x_pos = request.POST.get('x_pos', '0.5')
    y_pos = request.POST.get('y_pos', '0.5')

    if form.is_valid():
        element = MapElement(
            map=map_obj,
            element_type=element_type,
            x_pos=float(x_pos),
            y_pos=float(y_pos),
            is_conditional='is_conditional' in request.POST,
        )
        element.save()

        type_obj = form.save(commit=False)
        type_obj.element = element
        type_obj.save()

        # Bedingungen speichern
        for quest_id in request.POST.getlist('condition_quest'):
            if quest_id:
                ElementCondition.objects.create(
                    element=element,
                    required_quest_id=quest_id,
                    condition_type='quest_completed',
                    condition_value=quest_id,
                )

        response = render(request, 'maps/partials/element_form_success.html', {
            'element': element,
        })
        response['HX-Trigger'] = json.dumps({'elementAdded': element.to_dict()})
        return response

    quests = map_obj.map_set.quests.all()
    return render(request, f'maps/partials/element_form_{element_type}.html', {
        'form': form,
        'map': map_obj,
        'x_pos': x_pos,
        'y_pos': y_pos,
        'quests': quests,
        'element_type': element_type,
    }, status=422)


@login_required
@require_POST
def element_delete(request, element_pk):
    """Löscht ein MapElement und sendet HX-Trigger."""
    element = get_object_or_404(MapElement.objects.select_related('map__map_set'), pk=element_pk)
    _check_mapset_owner(request, element.map.map_set)
    element_id = element.pk
    element.delete()
    from django.http import HttpResponse
    response = HttpResponse(status=200)
    response['HX-Trigger'] = json.dumps({'elementDeleted': {'id': element_id}})
    return response


@login_required
def element_modal(request, element_pk):
    """Gibt das Popup-Modal eines Elements als HTMX-Partial zurück."""
    element = get_object_or_404(
        MapElement.objects.select_related('map__map_set', 'npc', 'item', 'trigger'),
        pk=element_pk,
    )
    is_owner = element.map.map_set.owner == request.user or request.user.is_admin
    active_session = None if is_owner else _get_user_active_session(request.user, element.map)

    if not is_owner and not active_session:
        from django.http import HttpResponse
        return HttpResponse(status=403)

    templates = {
        'npc': 'maps/partials/element_modal_npc.html',
        'item': 'maps/partials/element_modal_item.html',
        'trigger': 'maps/partials/element_modal_trigger.html',
    }
    return render(request, templates[element.element_type], {
        'element': element,
        'active_session': active_session,
        'is_owner': is_owner,
    })


@login_required
@require_POST
def element_action(request, element_pk):
    """Verarbeitet eine Spieler-Aktion auf einem Element (Annehmen, Nehmen, Aktivieren …)."""
    element = get_object_or_404(MapElement.objects.select_related('map'), pk=element_pk)
    action = request.POST.get('action', '')

    active_session = _get_user_active_session(request.user, element.map)
    if not active_session:
        from django.http import HttpResponse
        return HttpResponse(status=403)

    from sessions.models import SessionParticipant, SessionEvent
    try:
        participant = active_session.participants.get(user=request.user, is_removed=False)
    except SessionParticipant.DoesNotExist:
        from django.http import HttpResponse
        return HttpResponse(status=403)

    event_map = {
        'accept':   'quest_accepted',
        'decline':  'quest_declined',
        'take':     'item_taken',
        'activate': 'trigger_activated',
        'yes':      'npc_response',
        'no':       'npc_response',
    }
    event_type = event_map.get(action)
    if not event_type:
        from django.http import HttpResponse
        return HttpResponse(status=400)

    SessionEvent.objects.create(
        session=active_session,
        character=participant.character,
        element=element,
        event_type=event_type,
    )

    if action == 'take':
        from inventory.models import InventoryItem
        InventoryItem.objects.get_or_create(
            character=participant.character,
            map_element=element,
            session=active_session,
        )

    from django.http import HttpResponse
    response = HttpResponse(status=200)
    response['HX-Trigger'] = json.dumps({
        'elementActionDone': {'action': action, 'element_id': element.pk},
    })
    return response
