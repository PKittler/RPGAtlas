from django.urls import path, include

from . import views

app_name = 'adminpanel'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # User-Verwaltung
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # Karten-Set-Verwaltung
    path('mapsets/', views.mapset_list, name='mapset_list'),
    path('mapsets/<int:pk>/delete/', views.mapset_delete, name='mapset_delete'),

    # Werbung
    path('advertising/', include('advertising.urls')),
]
