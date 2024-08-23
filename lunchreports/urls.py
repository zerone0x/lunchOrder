from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("order_report/", views.lunch_report, name="order_report"),
    path("combined_order_report/",
         views.combined_lunch_report,
         name="combined_order_report")
]
