import pytest
from types import SimpleNamespace

from UsersAPI.domains.inventory.services import product_image_service


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def configure_providers(monkeypatch):
    monkeypatch.setattr(
        product_image_service,
        "settings",
        SimpleNamespace(
            brave_search_api_key="brave-test-key",
            brave_images_url="https://brave.example/images",
            pexels_api_key="pexels-test-key",
            pexels_images_url="https://pexels.example/search",
        ),
    )


def test_search_product_images_uses_brave_first(monkeypatch):
    configure_providers(monkeypatch)
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
    assert calls[0][0] == "https://brave.example/images"
    assert calls[0][1]["headers"]["X-Subscription-Token"] == "brave-test-key"
    assert calls[0][1]["params"] == {
        "q": "Aguardiente Antioqueño Litro",
        "count": 12,
        "safesearch": "strict",
        "spellcheck": "true",
    }


def test_search_product_images_falls_back_to_pexels(monkeypatch):
    configure_providers(monkeypatch)
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url == "https://brave.example/images":
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

    assert calls == ["https://brave.example/images", "https://pexels.example/search"]
    assert result[0]["source"] == "PEXELS"
    assert result[0]["thumbnail_url"] == "https://images.pexels.com/small.jpg"


def test_search_product_images_requires_at_least_one_provider(monkeypatch):
    monkeypatch.setattr(
        product_image_service,
        "settings",
        SimpleNamespace(
            brave_search_api_key="",
            brave_images_url="",
            pexels_api_key="",
            pexels_images_url="",
        ),
    )

    with pytest.raises(product_image_service.HTTPException) as exc_info:
        product_image_service.search_product_images("cafe")

    assert exc_info.value.status_code == 503
