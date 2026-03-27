from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def home_view(request):
    return render(request, 'home.html')


def datenschutz_view(request):
    return render(request, 'datenschutz.html')


def impressum_view(request):
    return render(request, 'impressum.html')


def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)
