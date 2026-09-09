import os
from urllib.parse import urlparse

import requests
from fastapi import HTTPException, status


def _hostname(url: str | None) -> str | None:
    if not url:
        return None
    return urlparse(url).hostname


def _provider_url(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _search_brave(query: str, per_page: int, api_key: str, images_url: str) -> list[dict[str, str | int | None]]:
    response = requests.get(
        images_url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
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


def _search_pexels(query: str, per_page: int, api_key: str, images_url: str) -> list[dict[str, str | int | None]]:
    response = requests.get(
        images_url,
        headers={"Authorization": api_key},
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


def search_product_images(query: str, per_page: int = 12) -> list[dict[str, str | int | None]]:
    clean_query = query.strip()
    brave_key = os.getenv("BRAVE_SEARCH_API_KEY")
    pexels_key = os.getenv("PEXELS_API_KEY")
    brave_url = _provider_url("BRAVE_IMAGES_URL")
    pexels_url = _provider_url("PEXELS_IMAGES_URL")
    limit = min(max(per_page, 1), 20)

    if not brave_key and not pexels_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product image search is not configured. Set BRAVE_SEARCH_API_KEY or PEXELS_API_KEY.",
        )

    if brave_key and brave_url:
        try:
            results = _search_brave(clean_query, limit, brave_key, brave_url)
            if results:
                return results
        except requests.RequestException:
            pass

    if pexels_key and pexels_url:
        try:
            return _search_pexels(clean_query, limit, pexels_key, pexels_url)
        except requests.RequestException as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not retrieve product images.",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Product image search is not configured. Set the provider API key and URL environment variables.",
    )
