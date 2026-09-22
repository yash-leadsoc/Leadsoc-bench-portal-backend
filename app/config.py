import os

# Load a local .env file if python-dotenv is installed, so values in
# .env actually take effect (uvicorn does not read .env on its own).
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

SECRET = os.getenv("LEADSOC_SECRET", "dev-secret-change-me")
MONGO_URL = os.getenv("LEADSOC_MONGO_URL", "mongodb+srv://yashsoni9902_db_user:PRFv7TbUlUn3PxSL@cluster0.l82k5gk.mongodb.net")
DB_NAME = os.getenv("LEADSOC_DB_NAME", "leadsoc_tedp")
TOKEN_HOURS = int(os.getenv("LEADSOC_TOKEN_HOURS", "12"))
CORS_ORIGINS = os.getenv("LEADSOC_CORS_ORIGINS", "*").split(",")

ADMIN_EMAIL = os.getenv("LEADSOC_ADMIN_EMAIL", "admin@leadsoc.com")
ADMIN_PASSWORD = os.getenv("LEADSOC_ADMIN_PASSWORD", "admin123")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@leadsoc.com")


GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_REDIRECT_URI=os.getenv("GOOGLE_REDIRECT_URI", "")
GOOGLE_OAUTH_TOKEN=os.getenv("GOOGLE_OAUTH_TOKEN", "")
GOOGLE_CALENDAR_ID=os.getenv("GOOGLE_CALENDAR_ID", "")

# XAI_API_KEY = os.getenv("XAI_API_KEY", "")
# XAI_MODEL = os.getenv("XAI_MODEL", "grok-2-latest")
# XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", os.getenv("XAI_API_KEY", ""))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1") 

EMAIL_DOMAIN = "leadsoc.com"
EMP_ID_PREFIX = "LS"


# Cloudinary (file storage for Materials / Prep / Library uploads)
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")            # cloudinary://<api_key>:<api_secret>@<cloud_name>
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
