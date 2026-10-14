from django.urls import path
from .views import (
    ReportSummaryView,
    ReportPaymentsView,
    ReportDebtsView,
    ReportBranchesView,
    ReportExportView
)

urlpatterns = [
    path('summary/', ReportSummaryView.as_view(), name='report-summary'),
    path('payments/', ReportPaymentsView.as_view(), name='report-payments'),
    path('debts/', ReportDebtsView.as_view(), name='report-debts'),
    path('branches/', ReportBranchesView.as_view(), name='report-branches'),
    path('export/', ReportExportView.as_view(), name='report-export'),
]
