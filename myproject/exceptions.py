import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Log the full error if it's a 500 error or if no response was generated
    if response is None:
        logger.error("Unhandled exception in API:", exc_info=exc)
        return Response({
            'error': 'An unexpected error occurred. Please try again later.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
