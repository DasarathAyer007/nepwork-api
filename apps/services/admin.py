# Register your models here.

from django.contrib import admin

from .models import Service, ServiceCategory, ServiceRequest

admin.site.register(Service)
admin.site.register(ServiceCategory)
admin.site.register(ServiceRequest)
