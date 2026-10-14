from decimal import Decimal
from datetime import timedelta
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils import timezone
from apps.debts.models import Debt, DebtStatus
from apps.payments.models import Payment, PaymentMethod
from apps.customers.models import Customer
from apps.shops.models import Branch


class ReportService:
    @staticmethod
    def get_summary(shop, branch=None, start_date=None, end_date=None):
        """
        Calculates high-level financial summary, clearly distinguishing:
        - Total historical debt created
        - Actual valid payments collected (cash vs card)
        - Reversed payments
        - Current outstanding balance
        - Overdue debt
        """
        debts_qs = Debt.objects.filter(shop=shop)
        payments_qs = Payment.objects.filter(shop=shop)
        customers_qs = Customer.objects.filter(shop=shop)

        if branch:
            debts_qs = debts_qs.filter(branch=branch)
            payments_qs = payments_qs.filter(branch=branch)
            customers_qs = customers_qs.filter(branch=branch)

        # Apply date filters to flow queries
        debt_flow_qs = debts_qs
        payment_flow_qs = payments_qs
        if start_date:
            debt_flow_qs = debt_flow_qs.filter(debt_date__gte=start_date)
            payment_flow_qs = payment_flow_qs.filter(payment_date__date__gte=start_date)
        if end_date:
            debt_flow_qs = debt_flow_qs.filter(debt_date__lte=end_date)
            payment_flow_qs = payment_flow_qs.filter(payment_date__date__lte=end_date)

        # 1. Total Debt Created (in selected period if filtered, excluding CANCELLED)
        debt_created_agg = debt_flow_qs.exclude(status=DebtStatus.CANCELLED).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        total_debt_created = debt_created_agg['total'] or Decimal('0.00')

        # 2. Valid Payments Collected
        valid_payments = payment_flow_qs.filter(is_reversed=False)
        pay_agg = valid_payments.aggregate(
            total=Sum('amount'),
            cash=Sum('cash_amount'),
            card=Sum('card_amount'),
            count=Count('id')
        )
        total_payments_collected = pay_agg['total'] or Decimal('0.00')
        total_cash_collected = pay_agg['cash'] or Decimal('0.00')
        total_card_collected = pay_agg['card'] or Decimal('0.00')

        # 3. Reversed Payments
        reversed_payments = payment_flow_qs.filter(is_reversed=True)
        rev_agg = reversed_payments.aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        total_reversed_amount = rev_agg['total'] or Decimal('0.00')
        count_reversed_payments = rev_agg['count'] or 0

        # 4. Current Outstanding Balances (Snapshot as of right now)
        active_debts = debts_qs.exclude(status__in=[DebtStatus.CANCELLED, DebtStatus.PAID])
        outstanding_agg = active_debts.aggregate(
            outstanding=Sum('remaining_balance'),
            overdue=Sum('remaining_balance', filter=Q(status=DebtStatus.OVERDUE))
        )
        current_outstanding_debt = outstanding_agg['outstanding'] or Decimal('0.00')
        total_overdue_debt = outstanding_agg['overdue'] or Decimal('0.00')

        # 5. Counts and Statuses
        status_counts = debts_qs.aggregate(
            unpaid=Count('id', filter=Q(status=DebtStatus.UNPAID)),
            partially_paid=Count('id', filter=Q(status=DebtStatus.PARTIALLY_PAID)),
            paid=Count('id', filter=Q(status=DebtStatus.PAID)),
            overdue=Count('id', filter=Q(status=DebtStatus.OVERDUE)),
            cancelled=Count('id', filter=Q(status=DebtStatus.CANCELLED))
        )

        total_customers = customers_qs.filter(status='ACTIVE').count()
        active_debtors = customers_qs.filter(
            status='ACTIVE',
            debts__remaining_balance__gt=Decimal('0.00')
        ).distinct().count()

        return {
            "currency": shop.currency,
            "total_debt_created": total_debt_created,
            "total_payments_collected": total_payments_collected,
            "total_cash_collected": total_cash_collected,
            "total_card_collected": total_card_collected,
            "total_reversed_amount": total_reversed_amount,
            "count_reversed_payments": count_reversed_payments,
            "current_outstanding_debt": current_outstanding_debt,
            "total_overdue_debt": total_overdue_debt,
            "total_customers_count": total_customers,
            "active_debtors_count": active_debtors,
            "debt_counts_by_status": {
                "unpaid": status_counts['unpaid'],
                "partially_paid": status_counts['partially_paid'],
                "paid": status_counts['paid'],
                "overdue": status_counts['overdue'],
                "cancelled": status_counts['cancelled'],
            }
        }

    @staticmethod
    def get_payment_trends(shop, interval="daily", start_date=None, end_date=None, branch=None):
        """Aggregates payments by day, week, or month."""
        payments_qs = Payment.objects.filter(shop=shop, is_reversed=False)
        if branch:
            payments_qs = payments_qs.filter(branch=branch)
        if start_date:
            payments_qs = payments_qs.filter(payment_date__date__gte=start_date)
        if end_date:
            payments_qs = payments_qs.filter(payment_date__date__lte=end_date)

        if interval == "monthly":
            trunc_func = TruncMonth('payment_date')
        elif interval == "weekly":
            trunc_func = TruncWeek('payment_date')
        else:
            trunc_func = TruncDate('payment_date')

        trends = payments_qs.annotate(period=trunc_func).values('period').annotate(
            total_amount=Sum('amount'),
            cash_amount=Sum('cash_amount'),
            card_amount=Sum('card_amount'),
            transaction_count=Count('id')
        ).order_by('period')

        results = []
        for item in trends:
            results.append({
                "period": item['period'].strftime("%Y-%m-%d") if item['period'] else "",
                "total_amount": item['total_amount'] or Decimal('0.00'),
                "cash_amount": item['cash_amount'] or Decimal('0.00'),
                "card_amount": item['card_amount'] or Decimal('0.00'),
                "transaction_count": item['transaction_count']
            })
        return results

    @staticmethod
    def get_debt_analysis(shop, branch=None):
        """Returns aging brackets and top debtor customers."""
        debts_qs = Debt.objects.filter(
            shop=shop,
            remaining_balance__gt=Decimal('0.00')
        ).exclude(status=DebtStatus.CANCELLED)

        if branch:
            debts_qs = debts_qs.filter(branch=branch)

        today = timezone.localdate()

        # Aging brackets
        b0_30 = debts_qs.filter(debt_date__gte=today - timedelta(days=30)).aggregate(s=Sum('remaining_balance'))['s'] or Decimal('0.00')
        b31_60 = debts_qs.filter(
            debt_date__gte=today - timedelta(days=60),
            debt_date__lt=today - timedelta(days=30)
        ).aggregate(s=Sum('remaining_balance'))['s'] or Decimal('0.00')
        b61_90 = debts_qs.filter(
            debt_date__gte=today - timedelta(days=90),
            debt_date__lt=today - timedelta(days=60)
        ).aggregate(s=Sum('remaining_balance'))['s'] or Decimal('0.00')
        b90_plus = debts_qs.filter(debt_date__lt=today - timedelta(days=90)).aggregate(s=Sum('remaining_balance'))['s'] or Decimal('0.00')

        # Top 10 Debtors
        top_debtors = Customer.objects.filter(shop=shop).annotate(
            total_debt=Sum('debts__remaining_balance', filter=~Q(debts__status=DebtStatus.CANCELLED))
        ).filter(total_debt__gt=Decimal('0.00')).order_by('-total_debt')[:10]

        top_debtor_list = [
            {
                "customer_id": str(c.id),
                "full_name": c.full_name,
                "phone_number": c.phone_number,
                "outstanding_debt": c.total_debt
            }
            for c in top_debtors
        ]

        return {
            "aging_distribution": {
                "0_to_30_days": b0_30,
                "31_to_60_days": b31_60,
                "61_to_90_days": b61_90,
                "90_plus_days": b90_plus
            },
            "top_debtors": top_debtor_list
        }

    @staticmethod
    def get_branch_performance(shop, start_date=None, end_date=None):
        branches = shop.branches.all()
        results = []

        for b in branches:
            debts_qs = Debt.objects.filter(branch=b).exclude(status=DebtStatus.CANCELLED)
            payments_qs = Payment.objects.filter(branch=b, is_reversed=False)

            if start_date:
                debts_qs = debts_qs.filter(debt_date__gte=start_date)
                payments_qs = payments_qs.filter(payment_date__date__gte=start_date)
            if end_date:
                debts_qs = debts_qs.filter(debt_date__lte=end_date)
                payments_qs = payments_qs.filter(payment_date__date__lte=end_date)

            debt_total = debts_qs.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
            payment_total = payments_qs.aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
            outstanding = debts_qs.aggregate(s=Sum('remaining_balance'))['s'] or Decimal('0.00')

            results.append({
                "branch_id": str(b.id),
                "branch_name": b.name,
                "is_main": b.is_main,
                "total_debt_issued": debt_total,
                "total_payments_collected": payment_total,
                "outstanding_balance": outstanding
            })

        return results
