from django.contrib import admin

# Register your models here.

from webapp.models import Review, Users, Admin
admin.site.register(Review)
admin.site.register(Users)
admin.site.register(Admin)

