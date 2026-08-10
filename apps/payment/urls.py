from django.urls import path

from .views.payment_view import (
    InitiateKhaltiPaymentView,
    PaymentDetailView,
    VerifyKhaltiPaymentByPidxView,
    VerifyKhaltiPaymentView,
)
from .views.wallet_view import (
    AdminCompletePayoutView,
    AdminCreatePayoutView,
    AdminWalletListView,
    MyPayoutsView,
    MyWalletView,
)

urlpatterns = [
    path(
        "khalti/initiate/",
        InitiateKhaltiPaymentView.as_view(),
        name="khalti-initiate",
    ),
    path(
        "khalti/verify/",
        VerifyKhaltiPaymentByPidxView.as_view(),
        name="khalti-verify-by-pidx",
    ),
    path(
        "khalti/<uuid:pk>/verify/",
        VerifyKhaltiPaymentView.as_view(),
        name="khalti-verify",
    ),
    path("<uuid:pk>/", PaymentDetailView.as_view(), name="payment-detail"),
    path("wallet/me/", MyWalletView.as_view(), name="wallet-me"),
    path(
        "wallet/me/payouts/", MyPayoutsView.as_view(), name="wallet-my-payouts"
    ),
    path(
        "wallet/admin/wallets/",
        AdminWalletListView.as_view(),
        name="wallet-admin-list",
    ),
    path(
        "wallet/admin/payouts/",
        AdminCreatePayoutView.as_view(),
        name="wallet-admin-create-payout",
    ),
    path(
        "wallet/admin/payouts/<uuid:pk>/complete/",
        AdminCompletePayoutView.as_view(),
        name="wallet-admin-complete-payout",
    ),
]
