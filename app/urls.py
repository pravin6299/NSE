from django.contrib import admin
from django.urls import path
from app.views import index
from . import views

urlpatterns = [
    path('', index, name='index'),
    path('instruments/', views.instrument_list, name='instrument_list'),
    path('instruments/<int:instrument_id>/', views.instrument_detail, name='instrument_detail'),
    path('stocks/', views.stock_market_view, name='stock_market'),
    path('stock/<str:symbol>/', views.stock_detail_view, name='stock_detail'),
    path('generate-token/', views.generate_token, name='generate_token'),
] 