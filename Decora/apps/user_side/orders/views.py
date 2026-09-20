
from django.contrib import messages
from apps.admin_side.orders.models import Order,OrderItem
from .services import OrderCancellationService,OrderReturnService,ReviewService
from django.http import HttpResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.template.loader import render_to_string
from weasyprint import HTML
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from apps.admin_side.coupons.models import CouponUsage
from apps.admin_side.orders.models import Order, OrderItem, OrderPayment   
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP






def _get_order_coupon_discount(order): 
    diff = (order.subtotal + order.shipping_charge) - order.total_amount
    return diff if diff > 0 else Decimal('0')
@login_required
def order_detail(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)

    order_items = OrderItem.objects.filter(order=order).select_related(
        "product", "variant", "combination"
    )

    payment = None
    if order.payment_method == "RAZORPAY":
        payment = OrderPayment.objects.filter(order=order).first()

    if order.payment_method == "COD":
        payment_status = "PAID" if order.status == "DELIVERED" else "PENDING"
    elif order.payment_method == "RAZORPAY":
        if not payment:
            payment_status = "PENDING"
        elif payment.status == "SUCCESS":
            payment_status = "PAID"
        elif payment.status == "FAILED":
            payment_status = "FAILED"
        else:
            payment_status = "PENDING"
    elif order.payment_method == "WALLET":
        payment_status = "PAID"
    else:
        payment_status = "PENDING"

    tracking_steps = [
            (True, "Order Placed"),
            (order.status in ("SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED"), "Shipped"),
            (order.status in ("OUT_FOR_DELIVERY", "DELIVERED"), "Out For Delivery"),
            (order.status == "DELIVERED", "Delivered"),
        ]

    context = {
            "order": order,
            "order_items": order_items,
            "payment": payment,
            "payment_status": payment_status,
            "tracking_steps": tracking_steps,
            "coupon_discount": _get_order_coupon_discount(order),
        }

    return render(request, "user_side/checkout/order_detail.html", context)
@login_required
def cancel_item(request, item_id):

    if request.method == "POST":

        order = get_object_or_404(
            Order,
            items__id=item_id,
            user=request.user
        )

        try:

            reason = request.POST.get(
                "cancellation_reason"
            )

            OrderCancellationService.cancel_item(
                order,
                item_id
            )
            messages.success(
                request,
                "Item cancelled successfully."
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "order_detail"
        )
    )
@login_required
def cancel_order(request, order_id):

    if request.method == "POST":

        order = get_object_or_404(
            Order,
            id=order_id,
            user=request.user
        )

        try:
            reason = request.POST.get(
                "cancellation_reason"
            )

            OrderCancellationService.cancel_order(
                order,
                reason
            )
            messages.success(request, "Order cancelled successfully.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect("order_detail", order_id=order_id)



from apps.admin_side.orders.models import Order, OrderItem, OrderPayment
from apps.admin_side.coupons.models import CouponUsage
from decimal import Decimal


def _get_order_coupon_discount(order):
    diff = (order.subtotal + order.shipping_charge) - order.total_amount
    return diff if diff > 0 else Decimal('0')


def _build_invoice_context(order):
    all_items = list(order.items.select_related('product').all())
    total = len(all_items)

    cancelled_items = [i for i in all_items if i.status == 'CANCELLED']
    returned_items = [i for i in all_items if i.status == 'RETURNED']
    non_cancelled_items = [i for i in all_items if i.status != 'CANCELLED']

    is_fully_cancelled = total > 0 and len(cancelled_items) == total
    is_fully_returned = total > 0 and len(returned_items) == total
    is_partial_cancel = 0 < len(cancelled_items) < total and len(returned_items) == 0
    is_partial_return = 0 < len(returned_items) < total

    payment = None
    if order.payment_method == "RAZORPAY":
        payment = OrderPayment.objects.filter(order=order).first()
    is_payment_failed = order.payment_method == "RAZORPAY" and payment and payment.status == "FAILED"

    if is_payment_failed:
        payment_status = "FAILED"
    elif is_fully_cancelled or is_fully_returned:
        payment_status = "NOT_APPLICABLE" if order.payment_method == "COD" else "REFUNDED"
    elif is_partial_return:
        payment_status = "NOT_APPLICABLE" if order.payment_method == "COD" else "PARTIALLY_REFUNDED"
    elif order.status == "DELIVERED":
        payment_status = "PAID"
    else:
        payment_status = "PENDING" if order.payment_method == "COD" else "PAID"

    subtotal_non_cancelled = sum((i.total_price for i in non_cancelled_items), Decimal('0'))
    refunded_amount = sum((i.total_price for i in returned_items), Decimal('0'))
    payable_amount = order.total_amount if not is_partial_cancel else subtotal_non_cancelled

    coupon_discount = _get_order_coupon_discount(order)
    coupon_usage = CouponUsage.objects.filter(order=order).select_related('coupon').first()

    notes = []
    if is_payment_failed:
        notes = [
            "Your payment could not be completed.",
            "Please retry your payment to continue processing your order.",
        ]
    elif is_fully_cancelled:
        if order.payment_method == "COD":
            notes = [
                "This order has been cancelled.",
                "Since this was a Cash on Delivery order, no payment was collected.",
                "Thank you for choosing Decora.",
            ]
        else:
            notes = [
                "Your order has been cancelled successfully.",
                "Your payment has been refunded.",
                "Refunds usually appear in your original payment method according to your bank or payment provider's processing time.",
                "Thank you for shopping with Decora.",
            ]
    elif is_fully_returned:
        notes = [
            "Your return has been completed successfully.",
            "The refunded amount has been processed.",
            "Thank you for shopping with Decora.",
        ]
    elif is_partial_cancel:
        notes = [
            "Cancelled items have been excluded from the payable amount.",
            "Remaining items are being processed.",
        ]
        if order.payment_method == "COD":
            notes.append(f"Please pay only ₹{payable_amount} upon delivery.")
    elif is_partial_return:
        notes = [
            "Some items were returned and refunded.",
            "Delivered items remain part of the completed order.",
            "The refund has been processed for the returned products.",
            "Thank you for shopping with Decora.",
        ]
    elif order.status == "DELIVERED":
        if order.payment_method == "COD":
            notes = [
                "Your order has been delivered successfully.",
                f"Cash on Delivery payment of ₹{order.total_amount} has been received.",
                "Thank you for shopping with Decora.",
            ]
        else:
            notes = [
                "Your order has been delivered successfully.",
                "Payment has already been received.",
                "Thank you for shopping with Decora.",
            ]
    elif order.status == "SHIPPED":
        notes = ["Your order has been shipped.", "You can expect delivery within the estimated delivery period."]
        if order.payment_method == "COD":
            notes.append(f"Please keep ₹{order.total_amount} ready for Cash on Delivery.")
    elif order.status == "OUT_FOR_DELIVERY":
        notes = ["Your package is out for delivery.", "Please be available to receive your order."]
        if order.payment_method == "COD":
            notes.append(f"Please keep ₹{order.total_amount} ready for Cash on Delivery.")
    else:  
        notes = [
            "Your order has been confirmed successfully.",
            "Our team is preparing your items.",
            "Your order will be shipped soon.",
        ]
        if order.payment_method == "COD":
            notes.append(f"Please keep ₹{order.total_amount} ready for Cash on Delivery.")

    return {
    "order": order,
    "order_items": all_items,
    "payment": payment,
    "payment_status": payment_status,
    "is_payment_failed": is_payment_failed,
    "is_fully_cancelled": is_fully_cancelled,
    "is_fully_returned": is_fully_returned,
    "is_partial_cancel": is_partial_cancel,
    "is_partial_return": is_partial_return,
    "is_terminal": is_fully_cancelled or is_fully_returned,
    "cancelled_items": cancelled_items,
    "returned_items": returned_items,
    "subtotal_non_cancelled": subtotal_non_cancelled,
    "refunded_amount": refunded_amount,
    "payable_amount": payable_amount,
    "coupon_discount": coupon_discount,
    "coupon_usage": coupon_usage,
    "notes": notes,
}


@login_required
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = _build_invoice_context(order)

    html_string = render_to_string("user_side/invoice.html", context)

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{order.order_id}.pdf"'
    return response
@login_required
def write_review(request, item_id):

    order_item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__user=request.user
    )

    if request.method == "POST":

        try:

            ReviewService.create_review(
                order_item=order_item,
                user=request.user,
                rating=request.POST.get("rating"),
                comment=request.POST.get("comment")
            )

            messages.success(
                request,
                "Review submitted successfully."
            )

            return redirect(
        "order_detail",
        order_item.order.id
    )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return render(
        request,
        "user_side/checkout/write_review.html",
        {
            "item": order_item
        }
    )
@login_required
def return_item(request, item_id):

    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order__user=request.user
    )

    if request.method == "POST":

        reason = request.POST.get(
            "return_reason"
        )

        try:

            OrderReturnService.request_return(
                item,
                reason
            )

            messages.success(
                request,
                "Return request submitted successfully."
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

    return redirect(
        "order_detail",
        order_id=item.order.id
    )