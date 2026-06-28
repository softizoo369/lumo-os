from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from apps.saas_core.services.stripe_service import StripeService

@csrf_exempt
def stripe_webhook_receiver(request):
    """
    Receives Background Events from Stripe (No CSRF Required).
    Only strictly validated payloads are processed.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not payload or not sig_header:
        return HttpResponse("Missing payload or signature", status=400)

    try:
        # পুরো কাজ StripeService-এর ওপর ছেড়ে দিচ্ছি
        StripeService.process_webhook_event(payload, sig_header)
        return HttpResponse("Webhook Processed Successfully", status=200)
    except ValueError as e:
        return HttpResponse(str(e), status=400)
    except Exception as e:
        # সার্ভার এরর হলেও 400 পাঠাবো যাতে Stripe পরে আবার রি-ট্রাই করে
        return HttpResponse("Internal Server Error", status=400)