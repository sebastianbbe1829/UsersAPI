from urllib.parse import urlparse

import requests
from fastapi import HTTPException, status

from UsersAPI.settings import settings


def _hostname(url: str | None) -> str | None:
    if not url:
        return None
    return urlparse(url).hostname


def _search_brave(
    query: str,
    per_page: int,
) -> list[dict[str, str | int | None]]:
    response = requests.get(
        settings.brave_images_url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": settings.brave_search_api_key,
        },
        params={
            "q": query.strip(),
            "count": min(max(per_page, 1), 20),
            "country": "CO",
            "search_lang": "es",
            "safesearch": "strict",
            "spellcheck": "true",
        },
        timeout=10,
    )
    response.raise_for_status()

    payload = response.json()
    results = []
    for index, item in enumerate(payload.get("results", [])):
        properties = item.get("properties") or {}
        image_url = properties.get("url")
        thumbnail_url = (item.get("thumbnail") or {}).get("src")
        source_url = item.get("url")
        if not image_url or not thumbnail_url:
            continue

        hostname = _hostname(source_url)
        results.append(
            {
                "id": item.get("id") or f"brave-{index}",
                "url": image_url,
                "thumbnail_url": thumbnail_url,
                "source_url": source_url,
                "credit": hostname or item.get("title") or "Brave Search",
                "alt": item.get("title") or query.strip(),
                "source": "BRAVE",
            }
        )

    return results


def _search_pexels(
    query: str,
    per_page: int,
) -> list[dict[str, str | int | None]]:
    response = requests.get(
        settings.pexels_images_url,
        headers={"Authorization": settings.pexels_api_key},
        params={
            "query": query.strip(),
            "per_page": min(max(per_page, 1), 20),
            "orientation": "square",
            "locale": "es-ES",
        },
        timeout=10,
    )
    response.raise_for_status()

    payload = response.json()
    return [
        {
            "id": photo.get("id"),
            "url": photo.get("src", {}).get("medium"),
            "thumbnail_url": photo.get("src", {}).get("small"),
            "source_url": photo.get("url"),
            "credit": photo.get("photographer"),
            "alt": photo.get("alt"),
            "source": "PEXELS",
        }
        for photo in payload.get("photos", [])
        if photo.get("src", {}).get("medium")
    ]


def search_product_images(
    query: str,
    per_page: int = 12,
) -> list[dict[str, str | int | None]]:
    clean_query = query.strip()
    limit = min(max(per_page, 1), 20)

    if not settings.brave_search_api_key and not settings.pexels_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product image search is not configured. Set BRAVE_SEARCH_API_KEY or PEXELS_API_KEY.",
        )

    if settings.brave_search_api_key and settings.brave_images_url:
        try:
            results = _search_brave(clean_query, limit)
            if results:
                return results
        except requests.RequestException:
            pass

    if settings.pexels_api_key and settings.pexels_images_url:
        try:
            return _search_pexels(clean_query, limit)
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not retrieve product images.",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Product image search is not configured. Set the provider API key and URL environment variables.",
    )
