import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from maps.models import MapSet

from .forms import QuestForm, QuestStepForm
from .models import Quest, QuestStep


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _check_mapset_owner(request, mapset):
    if mapset.owner != request.user and not request.user.is_admin:
        raise PermissionDenied


# ---------------------------------------------------------------------------
# Quest-CRUD
# ---------------------------------------------------------------------------

@login_required
def quest_list(request, mapset_pk):
    mapset = get_object_or_404(MapSet, pk=mapset_pk)
    _check_mapset_owner(request, mapset)
    quests = mapset.quests.prefetch_related('steps').order_by('-created_at')
    return render(request, 'quests/quest_list.html', {
        'mapset': mapset,
        'quests': quests,
    })


@login_required
def quest_create(request, mapset_pk):
    mapset = get_object_or_404(MapSet, pk=mapset_pk)
    _check_mapset_owner(request, mapset)
    form = QuestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        quest = form.save(commit=False)
        quest.map_set = mapset
        quest.save()
        messages.success(request, f'Quest „{quest.title}" erstellt.')
        return redirect('quests:quest_detail', pk=quest.pk)
    return render(request, 'quests/quest_create.html', {'form': form, 'mapset': mapset})


@login_required
def quest_detail(request, pk):
    quest = get_object_or_404(Quest, pk=pk)
    _check_mapset_owner(request, quest.map_set)
    steps = quest.steps.order_by('order')
    step_form = QuestStepForm()
    return render(request, 'quests/quest_detail.html', {
        'quest': quest,
        'steps': steps,
        'step_form': step_form,
    })


@login_required
def quest_edit(request, pk):
    quest = get_object_or_404(Quest, pk=pk)
    _check_mapset_owner(request, quest.map_set)
    form = QuestForm(request.POST or None, instance=quest)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Quest aktualisiert.')
        return redirect('quests:quest_detail', pk=quest.pk)
    return render(request, 'quests/quest_edit.html', {'form': form, 'quest': quest})


@login_required
def quest_delete(request, pk):
    quest = get_object_or_404(Quest, pk=pk)
    _check_mapset_owner(request, quest.map_set)
    mapset_pk = quest.map_set_id
    if request.method == 'POST':
        title = quest.title
        quest.delete()
        messages.success(request, f'Quest „{title}" gelöscht.')
        return redirect('quests:quest_list', mapset_pk=mapset_pk)
    return render(request, 'quests/quest_delete.html', {'quest': quest})


# ---------------------------------------------------------------------------
# Quest-Schritte
# ---------------------------------------------------------------------------

@login_required
@require_POST
def step_add(request, quest_pk):
    quest = get_object_or_404(Quest, pk=quest_pk)
    _check_mapset_owner(request, quest.map_set)
    form = QuestStepForm(request.POST)
    if form.is_valid():
        max_order = quest.steps.aggregate(m=Max('order'))['m'] or 0
        step = form.save(commit=False)
        step.quest = quest
        step.order = max_order + 1
        step.save()
    return redirect('quests:quest_detail', pk=quest_pk)


@login_required
@require_POST
def step_delete(request, step_pk):
    step = get_object_or_404(QuestStep.objects.select_related('quest__map_set'), pk=step_pk)
    _check_mapset_owner(request, step.quest.map_set)
    quest_pk = step.quest_id
    step.delete()
    # Reihenfolge neu normalisieren
    for i, s in enumerate(QuestStep.objects.filter(quest_id=quest_pk).order_by('order'), start=1):
        if s.order != i:
            s.order = i
            s.save(update_fields=['order'])
    return redirect('quests:quest_detail', pk=quest_pk)


@login_required
@require_POST
def step_reorder(request, quest_pk):
    """Empfängt JSON {'order': [step_pk, ...]} und schreibt order-Werte neu."""
    quest = get_object_or_404(Quest, pk=quest_pk)
    _check_mapset_owner(request, quest.map_set)
    try:
        data = json.loads(request.body)
        order_list = data.get('order', [])
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'invalid'}, status=400)
    for i, step_pk in enumerate(order_list, start=1):
        QuestStep.objects.filter(pk=step_pk, quest=quest).update(order=i)
    return JsonResponse({'ok': True})
