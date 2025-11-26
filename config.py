import os

# Stripe configuration using environment variables only
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
