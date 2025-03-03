
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/',views.register,name='register' ),
    path('profile/', views.profile, name='profile'),  
         path('dashboard/', views.dashboard, name='dashboard'),
     path('dashboard/product/', views.product, name='product'),
      path('dashboard/city/', views.city, name='city'),
       path('dashboard/sales/', views.sales, name='sales'),
        path('dashboard/weather/', views.weather, name='weather'),
         path('dashboard/notification/', views.notification ,name='notification'),
    
   
] 