from django.db import transaction
from django.core.exceptions import ValidationError
from apps.user_side.accounts.models import Wallet, WalletTransaction


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


class AdminReturnService:

    @staticmethod
    @transaction.atomic
    def approve_return(item):

        if item.status != "RETURN_REQUESTED":
            raise ValidationError("Invalid request.")

        item.status = "RETURNED"
        item.save()

        item.combination.stock_quantity += item.quantity
        item.combination.save()

        order = item.order


        _credit_wallet(
            user=order.user,
            amount=item.total_price,
            purpose='return_refund',
        )

        remaining_active = order.items.exclude(
            status__in=["RETURNED", "CANCELLED"]
        ).count()

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