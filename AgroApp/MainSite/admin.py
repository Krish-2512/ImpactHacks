
from django.contrib import admin
from .models import CustomUser , Product, Notification # Import your custom user model

admin.site.register(CustomUser)

admin.site.register(Product)




admin.site.register(Notification)