# leads/views.py
import json
import logging
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from leads.tasks import _save_new_leads

logger = logging.getLogger(__name__)

@csrf_exempt
def freelancer_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Distill will send a JSON object – we'll normalise it
            lead_data = {
                'title': data.get('title', 'No Title'),
                'url': data.get('url', ''),
                'budget': data.get('budget', ''),
                'description': data.get('description', ''),
                'tech_stack': data.get('skills', []),
                'source': 'freelancer_distill',
                'client_name': data.get('client_name', ''),
                'client_country': data.get('client_country', ''),
            }
            result = _save_new_leads([lead_data])
            return JsonResponse({'status': 'ok', 'saved': result['saved']})
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'POST only'}, status=405)

def get_faqs(request):
    """
    API endpoint for Telegram bot to fetch active FAQs.
    """
    from .models import FAQ
    category = request.GET.get('category')
    
    faqs_qs = FAQ.objects.filter(is_active=True)
    if category:
        faqs_qs = faqs_qs.filter(category=category)
    
    faqs_data = []
    for faq in faqs_qs:
        faqs_data.append({
            'id': faq.id,
            'question': faq.question,
            'answer': faq.answer,
            'category': faq.category,
        })
    
    return JsonResponse({'status': 'success', 'faqs': faqs_data})
