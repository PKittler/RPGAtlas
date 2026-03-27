from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

handler404 = 'rpgatlas.views.handler404'
handler500 = 'rpgatlas.views.handler500'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('maps/', include('maps.urls')),
    path('characters/', include('characters.urls')),
    path('sessions/', include('sessions.urls')),
    path('quests/', include('quests.urls')),
    path('inventory/', include('inventory.urls')),
    path('admin-panel/', include('adminpanel.urls')),
    path('datenschutz/', views.datenschutz_view, name='datenschutz'),
    path('impressum/', views.impressum_view, name='impressum'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
