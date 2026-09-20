from django.db import transaction
from django.core.exceptions import ValidationError
from apps.user_side.accounts.models import Wallet, WalletTransaction
from decimal import Decimal

from decimal import Decimal, ROUND_HALF_UP


def _get_order_coupon_discount(order):
    diff = (order.subtotal + order.shipping_charge) - order.total_amount
    return diff if diff > 0 else Decimal('0')


def _item_refund_amount(item):
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
        wallet=wallet,amount=amount,
        transaction_type='credit',purpose=purpose,
    )


class AdminReturnService:
    
    @staticmethod
    @transaction.atomic
    def approve_return(item):
        if item.status != "RETURN_REQUESTED":
            raise ValidationError("Invalid request.")
        
        order = item.order
        product_discount = order.original_amount - order.subtotal
        coupon_discount = order.discount_amount - product_discount

        if coupon_discount < 0:
            coupon_discount = Decimal("0")

        if order.subtotal > 0 and coupon_discount > 0:
            item_coupon_discount = (coupon_discount * item.total_price / order.subtotal)
        else:
            item_coupon_discount = Decimal("0")

        refund_amount = item.total_price - item_coupon_discount

        if refund_amount < 0:
                refund_amount = Decimal("0")

        item.status = "RETURNED"
        item.save()
        item.combination.stock_quantity += item.quantity
        item.combination.save()

        _credit_wallet(user=order.user,amount=_item_refund_amount(item),purpose='return_refund',)
        remaining_active = order.items.exclude(status__in=["RETURNED", "CANCELLED"]).count()

        if remaining_active == 0:
            order.status = "RETURNED"
            order.save(update_fields=["status"])

        return item

    @staticmethod
    def reject_return(item):
        if item.status != "RETURN_REQUESTED":
            raise ValidationError("Invalid request.")

        item.status = "RETURN_REJECTED"
        item.save()
        order = item.order

        if order.status == "RETURN_REQUESTED":
            order.status = "DELIVERED"
            order.save()
        return item