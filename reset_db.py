"""Drop all data and reseed only the admin + system config (no demo)."""
import os
os.environ["LEADSOC_SEED_DEMO"] = "0"  # ensure demo data does NOT come back

from app import config
from app.database import client, get_db
from app.seed import seed

client.drop_database(config.DB_NAME)
print(f"Dropped database: {config.DB_NAME}")

seed(get_db())  # recreates admin + integrations/SLA/templates/weights only
print("Reseeded admin + system config. No demo data.")
print(f"Admin: {config.ADMIN_EMAIL} / {config.ADMIN_PASSWORD}")