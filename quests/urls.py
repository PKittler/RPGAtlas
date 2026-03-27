from django.urls import path

from . import views

app_name = 'quests'

urlpatterns = [
    # Quest-Liste pro MapSet
    path('<int:mapset_pk>/', views.quest_list, name='quest_list'),
    path('<int:mapset_pk>/create/', views.quest_create, name='quest_create'),

    # Quest-Detail + CRUD
    path('quest/<int:pk>/', views.quest_detail, name='quest_detail'),
    path('quest/<int:pk>/edit/', views.quest_edit, name='quest_edit'),
    path('quest/<int:pk>/delete/', views.quest_delete, name='quest_delete'),

    # Schritte
    path('quest/<int:quest_pk>/steps/add/', views.step_add, name='step_add'),
    path('quest/<int:quest_pk>/steps/reorder/', views.step_reorder, name='step_reorder'),
    path('steps/<int:step_pk>/delete/', views.step_delete, name='step_delete'),
]
