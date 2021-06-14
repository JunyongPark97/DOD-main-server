from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payment.views import DepositInfoAPIView

app_name = 'payment'


router = DefaultRouter()
router.register('deposit-info', DepositInfoAPIView, basename='deposit-info')

urlpatterns = [
    path('', include(router.urls)),
]