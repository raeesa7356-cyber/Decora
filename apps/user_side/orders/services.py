from django.db import transaction
from django.core.exceptions import ValidationError
from apps.admin_side.orders.models import OrderItem
from apps.user_side.accounts.models import Wallet, WalletTransaction
from .models import Review
from django.utils import timezone

from decimal import Decimal, ROUND_HALF_UP


from decimal import Decimal, ROUND_HALF_UP


def _get_order_coupon_discount(order):
    diff = (order.subtotal + order.shipping_charge) - order.total_amount
    return diff if diff > 0 else Decimal('0')


def _item_refund_amount(item):
    """Item's paid price minus its proportional share of any coupon discount."""
    order = item.order
    coupon_discount = _get_order_coupon_discount(order)

    if coupon_discount > 0 and order.subtotal > 0:
        item_share = (item.total_price / order.subtotal) * coupon_discount
        item_share = item_share.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        item_share = Decimal('0')

    return max(item.total_price - item_share, Decimal('0'))
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

     
        combo = item.combination
        combo.stock_quantity += item.quantity
        combo.save()

        if order.payment_method in ('RAZORPAY', 'WALLET'):
            _credit_wallet(
        user=order.user,
        amount=_item_refund_amount(item),
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

            combo = item.combination
            combo.stock_quantity += item.quantity
            combo.save()

           
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
        item.return_requested_at=timezone.now()
        item.return_reason = reason
        item.save()

        return item