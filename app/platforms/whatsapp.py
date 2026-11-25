"""WhatsApp has no discovery API. Links come ONLY from wa.me / api.whatsapp.com links published on a
prospect's own website (see profile_extractor). Registered so platform_status reports it honestly."""
from app.platforms.base import register

class WhatsAppAdapter:
    name, method = "WhatsApp", "extracted_from_published_pages"
    async def discover(self, ctx):
        return []

adapter = register(WhatsAppAdapter())
