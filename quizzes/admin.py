from django.contrib import admin
from .models import Quiz


try:
    admin.site.unregister(Quiz)
except admin.sites.NotRegistered:
    pass
