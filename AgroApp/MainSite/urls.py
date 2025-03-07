
from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('register/',views.register,name='register' ),
    path('profile/', views.profile, name='profile'),  
    path('dashboard/', views.dashboard, name='dashboard'),
     path('dashboard/product/', views.product_list, name='product_list'),
         path('dashboard/product/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('dashboard/product/delete/<int:product_id>/', views.delete_product, name='delete_product'),
      path('dashboard/city/', views.city, name='city'),
      
        path('dashboard/weather/', views.weather, name='weather'),
         path('dashboard/notification/', views.notification_list ,name='notification'),
          path('notifications/', views.notification_list, name='notifications_api'),
         path('delete-notification/<int:notification_id>/', views.delete_notification, name='delete_notification'),
           path('dashboard/sales/', views.sales_page, name='sales_page'),
            path("farmers/", views.farmers_list, name="farmer_list"),
         path("farmer/<int:farmer_id>/products/", views.farmer_products, name="farmer_products"),
            path("purchase/<int:product_id>/", views.purchase_product, name="purchase_product"),
    # path('cart/', views.cart_view, name='cart_view'),
    # path('checkout/', views.checkout_view, name='checkout'),
             path("transactions/", views.transaction_history, name="transaction_history"),
            path('predict/', views.weather_prediction_view, name='weather_prediction'),
 
   
] 