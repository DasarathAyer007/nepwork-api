from decouple import config

KHALTI_GATEWAY_URL = config("KHALTI_GATEWAY_URL")
KHALTI_SECRET_KEY = config("KHALTI_SECRET_KEY")
KHALTI_PUBLIC_KEY = config("KHALTI_PUBLIC_KEY")


APP_URL = config("APP_URL", default="http://localhost:8000")
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")
ADMIN_FRONTEND_URL = config(
    "ADMIN_FRONTEND_URL", default="http://localhost:5174"
)
