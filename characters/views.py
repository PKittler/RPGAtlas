from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CharacterForm
from .models import Character


@login_required
def character_list(request):
    characters = Character.objects.filter(owner=request.user).select_related('current_session')
    return render(request, 'characters/character_list.html', {'characters': characters})


@login_required
def character_create(request):
    form = CharacterForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        char = form.save(commit=False)
        char.owner = request.user
        char.save()
        messages.success(request, f'Figur „{char.name}" erstellt.')
        return redirect('characters:character_list')
    return render(request, 'characters/character_create.html', {'form': form})


@login_required
def character_edit(request, pk):
    char = get_object_or_404(Character, pk=pk)
    if char.owner != request.user and not request.user.is_admin:
        raise PermissionDenied
    locked = char.current_session_id is not None
    form = CharacterForm(request.POST or None, request.FILES or None, instance=char)
    if request.method == 'POST':
        if locked:
            messages.error(request, 'Figur ist in einer aktiven Session – bearbeiten nicht möglich.')
            return redirect('characters:character_list')
        if form.is_valid():
            form.save()
            messages.success(request, 'Figur aktualisiert.')
            return redirect('characters:character_list')
    return render(request, 'characters/character_edit.html', {
        'form': form,
        'char': char,
        'locked': locked,
    })


@login_required
def character_delete(request, pk):
    char = get_object_or_404(Character, pk=pk)
    if char.owner != request.user and not request.user.is_admin:
        raise PermissionDenied
    if char.current_session_id is not None:
        messages.error(request, 'Figur ist in einer aktiven Session – löschen nicht möglich.')
        return redirect('characters:character_list')
    if request.method == 'POST':
        name = char.name
        char.delete()
        messages.success(request, f'Figur „{name}" gelöscht.')
        return redirect('characters:character_list')
    return render(request, 'characters/character_delete.html', {'char': char})


@login_required
def character_detail(request, pk):
    char = get_object_or_404(Character.objects.select_related('owner', 'current_session'), pk=pk)
    return render(request, 'characters/character_detail.html', {'char': char})
