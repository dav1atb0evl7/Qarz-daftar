from decimal import Decimal
from rest_framework import views, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from .services import ReportService
from .serializers import (
    ReportSummarySerializer,
    PaymentTrendItemSerializer,
    BranchPerformanceItemSerializer
)
from .generators import ReportExporter
from apps.common.permissions import IsShopMember, get_requested_shop
from apps.debts.models import Debt
from apps.payments.models import Payment
from apps.audit.services import AuditService


class ReportSummaryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsShopMember]

    @extend_schema(
        summary="Get overall financial summary metrics",
        parameters=[
            OpenApiParameter('branch_id', str, required=False),
            OpenApiParameter('start_date', str, required=False),
            OpenApiParameter('end_date', str, required=False),
        ],
        responses={200: ReportSummarySerializer}
    )
    def get(self, request):
        shop = get_requested_shop(request)
        branch_id = request.query_params.get('branch_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        branch = shop.branches.filter(id=branch_id).first() if branch_id else None
        summary = ReportService.get_summary(
            shop=shop,
            branch=branch,
            start_date=start_date,
            end_date=end_date
        )
        return Response({"success": True, "data": summary})


class ReportPaymentsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsShopMember]

    @extend_schema(
        summary="Get payment collection trends (daily, weekly, monthly)",
        parameters=[
            OpenApiParameter('interval', str, enum=['daily', 'weekly', 'monthly'], default='daily'),
            OpenApiParameter('branch_id', str, required=False),
            OpenApiParameter('start_date', str, required=False),
            OpenApiParameter('end_date', str, required=False),
        ],
        responses={200: PaymentTrendItemSerializer(many=True)}
    )
    def get(self, request):
        shop = get_requested_shop(request)
        interval = request.query_params.get('interval', 'daily')
        branch_id = request.query_params.get('branch_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        branch = shop.branches.filter(id=branch_id).first() if branch_id else None
        trends = ReportService.get_payment_trends(
            shop=shop,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            branch=branch
        )
        return Response({"success": True, "data": trends})


class ReportDebtsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsShopMember]

    @extend_schema(
        summary="Get debt aging distribution and top debtors",
        responses={200: OpenApiResponse(description="Aging distribution and top debtors")}
    )
    def get(self, request):
        shop = get_requested_shop(request)
        branch_id = request.query_params.get('branch_id')
        branch = shop.branches.filter(id=branch_id).first() if branch_id else None

        analysis = ReportService.get_debt_analysis(shop=shop, branch=branch)
        return Response({"success": True, "data": analysis})


class ReportBranchesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsShopMember]

    @extend_schema(
        summary="Compare performance across all shop branches",
        responses={200: BranchPerformanceItemSerializer(many=True)}
    )
    def get(self, request):
        shop = get_requested_shop(request)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        results = ReportService.get_branch_performance(shop=shop, start_date=start_date, end_date=end_date)
        return Response({"success": True, "data": results})


class ReportExportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsShopMember]

    @extend_schema(
        summary="Export reports to CSV, Excel, or PDF",
        parameters=[
            OpenApiParameter('type', str, enum=['summary', 'debts', 'payments'], default='debts'),
            OpenApiParameter('format', str, enum=['csv', 'xlsx', 'pdf'], default='xlsx'),
            OpenApiParameter('start_date', str, required=False),
            OpenApiParameter('end_date', str, required=False),
        ],
        responses={200: OpenApiResponse(description="Exported report binary stream (CSV, Excel, or PDF)")}
    )
    def perform_content_negotiation(self, request, force=False):
        # Return direct HttpResponse (CSV/Excel/PDF) bypassing DRF format suffix filtering
        renderers = self.get_renderers()
        return (renderers[0], renderers[0].media_type)

    def get(self, request):
        shop = get_requested_shop(request)
        report_type = request.query_params.get('type', 'debts')
        export_format = request.query_params.get('format', 'xlsx').lower()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        filename = f"{shop.name}_{report_type}_report"

        AuditService.log_action(
            request=request,
            user=request.user,
            shop=shop,
            action="EXPORT_REPORT",
            entity_type="Report",
            entity_id=report_type,
            changes={"format": export_format, "start_date": start_date, "end_date": end_date}
        )

        if report_type == 'payments':
            headers = ['Kvitansiya', 'Sana', 'Mijoz', 'Telefon', 'Usul', 'Summa', 'Naqd', 'Karta', 'Qabul qildi', 'Bekor qilingan']
            payments = Payment.objects.filter(shop=shop).order_by('-payment_date')
            if start_date:
                payments = payments.filter(payment_date__date__gte=start_date)
            if end_date:
                payments = payments.filter(payment_date__date__lte=end_date)

            rows = [
                [
                    p.receipt_number,
                    p.payment_date.strftime("%Y-%m-%d %H:%M"),
                    p.customer.full_name,
                    p.customer.phone_number,
                    p.get_payment_method_display(),
                    p.amount,
                    p.cash_amount,
                    p.card_amount,
                    p.received_by.email,
                    "Ha" if p.is_reversed else "Yo'q"
                ]
                for p in payments
            ]
            title = f"{shop.name} - To'lovlar Hisoboti"

        elif report_type == 'summary':
            summary = ReportService.get_summary(shop=shop, start_date=start_date, end_date=end_date)
            headers = ['Ko\'rsatkich', 'Qiymat']
            rows = [
                ['Asosiy valyuta', summary['currency']],
                ['Yaratilgan jami qarz', summary['total_debt_created']],
                ['Yig\'ilgan to\'lovlar', summary['total_payments_collected']],
                ['Naqd tushum', summary['total_cash_collected']],
                ['Karta orqali tushum', summary['total_card_collected']],
                ['Bekor qilingan to\'lovlar', summary['total_reversed_amount']],
                ['Hozirgi qoldiq qarz', summary['current_outstanding_debt']],
                ['Muddati o\'tgan qarz', summary['total_overdue_debt']],
                ['Mijozlar soni', summary['total_customers_count']],
                ['Qarzdor mijozlar', summary['active_debtors_count']],
            ]
            title = f"{shop.name} - Moliyaviy Xulosa Hisoboti"

        else:  # 'debts' default
            headers = ['Mijoz', 'Telefon', 'Qarz Sanasi', 'Muddat', 'Umumiy Summa', 'To\'langan', 'Qoldiq Qarz', 'Holati']
            debts = Debt.objects.filter(shop=shop).order_by('-debt_date')
            if start_date:
                debts = debts.filter(debt_date__gte=start_date)
            if end_date:
                debts = debts.filter(debt_date__lte=end_date)

            rows = [
                [
                    d.customer.full_name,
                    d.customer.phone_number,
                    str(d.debt_date),
                    str(d.due_date or "-"),
                    d.amount,
                    d.paid_amount,
                    d.remaining_balance,
                    d.get_status_display()
                ]
                for d in debts
            ]
            title = f"{shop.name} - Qarzlar Daftari Hisoboti"

        if export_format == 'csv':
            return ReportExporter.export_csv(filename=filename, headers=headers, rows=rows)
        elif export_format == 'pdf':
            return ReportExporter.export_pdf(filename=filename, title=title, headers=headers, rows=rows)
        else:  # xlsx
            return ReportExporter.export_excel(filename=filename, sheet_title=report_type, headers=headers, rows=rows)
