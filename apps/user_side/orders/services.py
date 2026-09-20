from django.db import transaction
from django.core.exceptions import ValidationError
from apps.admin_side.orders.models import OrderItem
from apps.user_side.accounts.models import Wallet, WalletTransaction
from .models import Review


def _credit_wallet(user, amount, purpose):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet.balance += amount
    wallet.save()
    WalletTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        transaction_type='credit',
        purpose=purpose,
    )


class OrderCancellationService:

    @staticmethod
    def _can_cancel_order(order):
        return order.status == "PENDING"

    @staticmethod
    def _can_cancel_item(order, item):
        return (
    order.status == "PENDING"
    and item.status == "ACTIVE"
)

    @staticmethod
    @transaction.atomic
    def cancel_item(order, item_id, reason=None):
        item = OrderItem.objects.select_for_update().get(
            id=item_id, order=order
        )

        if not OrderCancellationService._can_cancel_item(order, item):
            raise ValidationError("Item cannot be cancelled.")

        item.status = "CANCELLED"
        item.cancellation_reason = reason
        item.save()

        # FIXED: stock lives on the combination now, not on separately
        # looked-up ProductVariant rows via a stale selected_options list.
        combo = item.combination
        combo.stock_quantity += item.quantity
        combo.save()

        if order.payment_method in ('RAZORPAY', 'WALLET'):
            _credit_wallet(
                user=order.user,
                amount=item.total_price,
                purpose='cancellation_refund',
            )

        if not order.items.filter(status="ACTIVE").exists():
            order.status = "CANCELLED"
            order.cancellation_reason = reason
            order.save()

        return item

    @staticmethod
    @transaction.atomic
    def cancel_order(order, reason=None):

        if not OrderCancellationService._can_cancel_order(order):
            raise ValidationError("Order cannot be cancelled.")

        active_items = list(order.items.filter(status="ACTIVE"))

        order.status = "CANCELLED"
        order.cancellation_reason = reason
        order.save()

        for item in active_items:
            item.status = "CANCELLED"
            item.cancellation_reason = reason
            item.save()

            # FIXED: same combination-based stock restore
            combo = item.combination
            combo.stock_quantity += item.quantity
            combo.save()

            # Refund the full order total for RAZORPAY and WALLET payments.
            # COD at PENDING stage: cash never collected, so no refund.
        if order.payment_method in ('RAZORPAY', 'WALLET'):
            _credit_wallet(
                user=order.user,
                amount=order.total_amount,
                purpose='cancellation_refund',
            )

        return order


class ReviewService:

    @staticmethod
    @transaction.atomic
    def create_review(*, order_item, user, rating, comment):
        allowed_statuses = ["ACTIVE", "RETURN_REQUESTED", "RETURNED"]

        if order_item.order.status != "DELIVERED":
            raise ValidationError("Review allowed only after delivery.")

        if order_item.status not in allowed_statuses:
            raise ValidationError("Review not allowed for this item.")

        if order_item.is_reviewed:
            raise ValidationError("You already reviewed this item.")

        review = Review.objects.create(
            user=user,
            product=order_item.product,
            order_item=order_item,
            rating=rating,
            comment=comment,
        )
        order_item.is_reviewed = True
        order_item.save()

        return review


class OrderReturnService:

    @staticmethod
    @transaction.atomic
    def request_return(item, reason):
        if item.status != "ACTIVE":
            raise ValidationError("Item cannot be returned.")

        if item.order.status != "DELIVERED":
            raise ValidationError("Only delivered items can be returned.")

        item.status = "RETURN_REQUESTED"
        item.return_reason = reason
        item.save()

        return item