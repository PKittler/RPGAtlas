from django.urls import path

from . import views

app_name = 'advertising'

urlpatterns = [
    # Partner
    path('partners/', views.partner_list, name='partner_list'),
    path('partners/create/', views.partner_create, name='partner_create'),
    path('partners/<int:pk>/edit/', views.partner_edit, name='partner_edit'),
    path('partners/<int:pk>/delete/', views.partner_delete, name='partner_delete'),

    # Kampagnen
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('campaigns/<int:pk>/deactivate/', views.campaign_deactivate, name='campaign_deactivate'),
    path('campaigns/<int:pk>/delete/', views.campaign_delete, name='campaign_delete'),

    # Icons
    path('icons/', views.icon_list, name='icon_list'),
    path('icons/create/', views.icon_create, name='icon_create'),
    path('icons/<int:pk>/edit/', views.icon_edit, name='icon_edit'),
    path('icons/<int:pk>/deactivate/', views.icon_deactivate, name='icon_deactivate'),
    path('icons/<int:pk>/delete/', views.icon_delete, name='icon_delete'),

    # Icon-Positions-Vorschau (AJAX)
    path('icons/map-preview/<int:map_pk>/', views.icon_map_preview, name='icon_map_preview'),
]
