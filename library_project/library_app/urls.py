# library_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.search_view, name='search'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkin/', views.checkin_view, name='checkin'),
    path('fines/', views.fines_view, name='fines'),
    path('add-borrower/', views.add_borrower_view, name='add-borrower'),
]