"""Email: extracted only where published (mailto:, page text, JSON-LD, YouTube descriptions, snippets)."""
from app.platforms.base import register

class EmailAdapter:
    name, method = "Email", "extracted_from_published_pages"
    async def discover(self, ctx):
        return []

adapter = register(EmailAdapter())
