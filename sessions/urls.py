from django.urls import path

from . import views

app_name = 'game_sessions'

urlpatterns = [
    # Übersicht
    path('', views.session_list, name='session_list'),

    # Anlegen
    path('create/', views.session_create, name='session_create'),

    # Beitreten
    path('join/<uuid:invite_token>/', views.session_join, name='session_join'),
    path('<int:pk>/waiting/', views.session_join_waiting, name='session_join_waiting'),
    path('<int:pk>/waiting/check/', views.join_status_check, name='join_status_check'),

    # Lobby
    path('<int:pk>/lobby/', views.session_lobby, name='session_lobby'),
    path('<int:pk>/lobby/participants/', views.lobby_participants, name='lobby_participants'),

    # Session-Aktionen
    path('<int:pk>/start/', views.session_start, name='session_start'),
    path('<int:pk>/end/', views.session_end, name='session_end'),
    path('<int:pk>/view/', views.session_view, name='session_view'),
    path('<int:pk>/change-map/', views.session_change_map, name='session_change_map'),

    # Teilnehmer-Verwaltung
    path('participant/<int:participant_pk>/confirm/', views.participant_confirm, name='participant_confirm'),
    path('participant/<int:participant_pk>/reject/', views.participant_reject, name='participant_reject'),
    path('participant/<int:participant_pk>/eliminate/', views.participant_eliminate, name='participant_eliminate'),
    path('participant/<int:participant_pk>/remove/', views.participant_remove, name='participant_remove'),

    # Positionsverlauf
    path('<int:session_pk>/character/<int:character_pk>/path/', views.character_path, name='character_path'),

    # Quest-Sidebar
    path('<int:session_pk>/quests/', views.quest_sidebar, name='quest_sidebar'),
    path('<int:session_pk>/quests/assign/', views.assign_quest_form, name='assign_quest_form'),
    path('<int:session_pk>/quests/assign/confirm/', views.assign_quest, name='assign_quest'),

    # Inventar-Sidebar
    path('<int:session_pk>/inventory/', views.inventory_sidebar, name='inventory_sidebar'),

    # CharacterQuest-Fortschritt
    path('cq/<int:cq_pk>/next-step/', views.character_quest_next_step, name='character_quest_next_step'),
    path('cq/<int:cq_pk>/complete/', views.character_quest_complete, name='character_quest_complete'),
    path('cq/<int:cq_pk>/fail/', views.character_quest_fail, name='character_quest_fail'),
]
