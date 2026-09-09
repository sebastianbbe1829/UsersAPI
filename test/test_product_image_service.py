import pytest

from UsersAPI.domains.inventory.services import product_image_service


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_search_product_images_uses_brave_first(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-test-key")
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test-key")
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            {
                "results": [
                    {
                        "id": "commercial-1",
                        "title": "Aguardiente Antioqueño Litro",
                        "url": "https://example.com/producto",
                        "thumbnail": {"src": "https://example.com/thumb.jpg"},
                        "properties": {"url": "https://example.com/product.jpg"},
                    }
                ]
            }
        )

    monkeypatch.setattr(product_image_service.requests, "get", fake_get)

    result = product_image_service.search_product_images("Aguardiente Antioqueño Litro", 12)

    assert result[0]["source"] == "BRAVE"
    assert result[0]["url"] == "https://example.com/product.jpg"
    assert result[0]["thumbnail_url"] == "https://example.com/thumb.jpg"
    assert result[0]["source_url"] == "https://example.com/producto"
    assert calls[0][0] == product_image_service.BRAVE_IMAGES_URL
    assert calls[0][1]["headers"]["X-Subscription-Token"] == "brave-test-key"
    assert calls[0][1]["params"]["country"] == "CO"
    assert calls[0][1]["params"]["search_lang"] == "es"


def test_search_product_images_falls_back_to_pexels(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-test-key")
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test-key")
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url == product_image_service.BRAVE_IMAGES_URL:
            raise product_image_service.requests.RequestException("Brave unavailable")
        return FakeResponse(
            {
                "photos": [
                    {
                        "id": 10,
                        "url": "https://pexels.com/photo/10",
                        "photographer": "Author",
                        "alt": "Producto",
                        "src": {
                            "medium": "https://images.pexels.com/medium.jpg",
                            "small": "https://images.pexels.com/small.jpg",
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr(product_image_service.requests, "get", fake_get)

    result = product_image_service.search_product_images("cafe", 12)

    assert calls == [product_image_service.BRAVE_IMAGES_URL, product_image_service.PEXELS_IMAGES_URL]
    assert result[0]["source"] == "PEXELS"
    assert result[0]["thumbnail_url"] == "https://images.pexels.com/small.jpg"


def test_search_product_images_requires_at_least_one_provider(monkeypatch):
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)

    with pytest.raises(product_image_service.HTTPException) as exc_info:
        product_image_service.search_product_images("cafe")

    assert exc_info.value.status_code == 503
