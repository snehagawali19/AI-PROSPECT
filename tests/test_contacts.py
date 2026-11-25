from app.utils.contacts import clean_email, clean_phone, whatsapp_from_link

def test_email_validation():
    assert clean_email("mailto:Hello@Acme-Bistro.ae?subject=hi") == "hello@acme-bistro.ae"
    assert clean_email("logo@2x.png") is None
    assert clean_email("someone@example.com") is None
    assert clean_email("not-an-email") is None

def test_phone_validation_respects_region():
    assert clean_phone("+971 2 234 5678", "AE") == "+97122345678"
    assert clean_phone("074104 10123", "IN") == "+917410410123"
    assert clean_phone("+44 20 7946 0958", "AE") is None          # valid UK number, wrong country
    assert clean_phone("12345", "US") is None

def test_whatsapp_only_from_published_links():
    assert whatsapp_from_link("https://wa.me/97122345678", "AE") == "https://wa.me/97122345678"
    assert whatsapp_from_link("https://api.whatsapp.com/send?phone=917410410123", "IN") == "https://wa.me/917410410123"
    assert whatsapp_from_link("https://example.com/contact", "AE") is None
