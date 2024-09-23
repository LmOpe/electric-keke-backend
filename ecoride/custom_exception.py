import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

class CustomException:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Exception as e:
            logger.error(f"A system error occured: {e}", exc_info=True)
            return JsonResponse({"message": "An unexpected error occured"}, status=500)
        return response