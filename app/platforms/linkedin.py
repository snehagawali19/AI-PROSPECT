from app.platforms.base import register
from app.platforms.serp_site import SiteSearchAdapter

adapter = register(SiteSearchAdapter("LinkedIn"))
