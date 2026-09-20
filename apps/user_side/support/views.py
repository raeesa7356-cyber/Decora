from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages


def contact_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        if not all([name, email, subject, message]):
            messages.error(request, "Please fill in all fields.")
            return render(request, "user_side/support/contact.html")

        try:
            send_mail(
                subject=f"[Decora Contact] {subject}",
                message=f"From: {name} <{email}>\n\n{message}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
            messages.success(request, "Your message has been sent. We'll get back to you soon.")
        except Exception:
            messages.error(request, "Something went wrong. Please try again.")

    return render(request, "user_side/support/contact.html")
