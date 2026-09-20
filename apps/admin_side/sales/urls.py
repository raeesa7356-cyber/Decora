from django.urls import path
from . import views

urlpatterns = [
    path("transactions/", views.wallet_transaction_list, name="wallet_transaction_list"),
    path("sales-report/", views.sales_report, name="sales_report"),
    path("sales-report/pdf/", views.download_sales_pdf, name="download_sales_pdf"),
    path("sales-report/excel/", views.download_sales_excel, name="download_sales_excel"),
]