from django.urls import path
from . import views

app_name = 'maps'

urlpatterns = [
    # MapSet
    path('', views.mapset_list, name='mapset_list'),
    path('create/', views.mapset_create, name='mapset_create'),
    path('<int:pk>/', views.mapset_detail, name='mapset_detail'),
    path('<int:pk>/edit/', views.mapset_edit, name='mapset_edit'),
    path('<int:pk>/delete/', views.mapset_delete, name='mapset_delete'),

    # Karten
    path('<int:mapset_pk>/add-map/', views.map_add, name='map_add'),
    path('map/<int:pk>/delete/', views.map_delete, name='map_delete'),
    path('map/<int:pk>/view/', views.map_view, name='map_view'),

    # Gates (HTMX)
    path('map/<int:map_pk>/gates/form/', views.gate_form, name='gate_form'),
    path('map/<int:map_pk>/gates/add/', views.gate_add, name='gate_add'),
    path('gates/<int:gate_pk>/delete/', views.gate_delete, name='gate_delete'),

    # Werbe-Icons (HTMX)
    path('ads/<int:ad_pk>/modal/', views.ad_modal, name='ad_modal'),
    path('ads/<int:ad_pk>/click/', views.ad_click, name='ad_click'),

    # Karten-Elemente (HTMX)
    path('map/<int:map_pk>/elements/type-select/', views.element_type_select, name='element_type_select'),
    path('map/<int:map_pk>/elements/form/<str:element_type>/', views.element_form, name='element_form'),
    path('map/<int:map_pk>/elements/add/', views.element_add, name='element_add'),
    path('elements/<int:element_pk>/delete/', views.element_delete, name='element_delete'),
    path('elements/<int:element_pk>/modal/', views.element_modal, name='element_modal'),
    path('elements/<int:element_pk>/action/', views.element_action, name='element_action'),
]
