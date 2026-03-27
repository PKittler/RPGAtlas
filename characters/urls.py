from django.urls import path

from . import views

app_name = 'characters'

urlpatterns = [
    path('', views.character_list, name='character_list'),
    path('create/', views.character_create, name='character_create'),
    path('<int:pk>/', views.character_detail, name='character_detail'),
    path('<int:pk>/edit/', views.character_edit, name='character_edit'),
    path('<int:pk>/delete/', views.character_delete, name='character_delete'),
]
