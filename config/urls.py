"""
Israinsols Pipeline - URL Configuration
"""
from django.contrib import admin
from django.urls import path
from leads.views import freelancer_webhook, get_faqs

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/webhook/freelancer/', freelancer_webhook, name='freelancer_webhook'),
    path('api/faqs/', get_faqs, name='get_faqs'),
]
