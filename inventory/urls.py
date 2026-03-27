from django.urls import path

from . import views

app_name = 'inventory'

urlpatterns = [
    path('<int:item_pk>/drop/', views.item_drop, name='item_drop'),
    path('<int:item_pk>/transfer/', views.item_transfer_form, name='item_transfer_form'),
    path('<int:item_pk>/transfer/confirm/', views.item_transfer, name='item_transfer'),
]
