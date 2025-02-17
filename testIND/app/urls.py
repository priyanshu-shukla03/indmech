from django.urls import path
from . import views
from .views import products_view
from django.conf import settings
from django.conf.urls.static import static
from .views import confirm_order

urlpatterns = [
    path('', views.user_login, name='user_login'),  # Default route redirects to login page
    path('logout/', views.user_logout, name='logout'), 
    path('home/', views.home, name='home'),    # Home page after successful login
    path('login/', views.user_login, name='user_login'),
    path('products/', products_view, name='products'),
    path('products/', views.products, name='products'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    # Cart page URL pattern
    path('cart/', views.cart, name='cart'),
    path('cart/mail', views.cart, name='cart'),
    # Update cart URL pattern (update or remove items)
    path('update_cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('order_history/', views.order_history, name='order_history'),
    path("confirm_order/<int:order_id>/", confirm_order, name="confirm_order"),
]

