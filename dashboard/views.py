from django.shortcuts import render

# Create your views here.
import json
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

@login_required(login_url='login')
def DashboardView(request):
    return render(request, 'dashboard/base_dashboard.html')

