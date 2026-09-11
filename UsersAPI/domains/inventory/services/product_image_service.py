from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from fastapi import HTTPException, status

from UsersAPI.settings import settings

logger = logging.getLogger(__name__)


def _valid_image_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _search_brave(query: str, limit: int) -> list[dict[str, str | int | None]]:
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": settings.brave_search_api_key,
    }
    params = {
        "q": query,
        "count": limit,
        "safesearch": "strict",
        "spellcheck": "true",
    }
    response = requests.get(
        settings.brave_images_url,
        headers=headers,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    results: list[dict[str, str | int | None]] = []

    for item in payload.get("results", []):
        properties = item.get("properties") or {}
        thumbnail = item.get("thumbnail") or {}
        image_url = properties.get("url")
        thumbnail_url = thumbnail.get("src")
        source_url = item.get("url")
        if not _valid_image_url(image_url) or not _valid_image_url(thumbnail_url):
            continue
        results.append(
            {
                "url": image_url,
                "thumbnail_url": thumbnail_url,
                "source": "BRAVE",
                "source_url": source_url if _valid_image_url(source_url) else None,
                "credit": item.get("title"),
            }
        )
        if len(results) >= limit:
            break

    return results


def _search_pexels(query: str, limit: int) -> list[dict[str, str | int | None]]:
    headers = {"Authorization": settings.pexels_api_key}
    params = {"query": query, "per_page": limit}
    response = requests.get(
        settings.pexels_images_url,
        headers=headers,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    results: list[dict[str, str | int | None]] = []

    for item in payload.get("photos", []):
        src = item.get("src") or {}
        image_url = src.get("original") or src.get("large") or src.get("medium")
        thumbnail_url = src.get("small") or src.get("medium") or image_url
        source_url = item.get("url")
        if not _valid_image_url(image_url) or not _valid_image_url(thumbnail_url):
            continue
        results.append(
            {
                "url": image_url,
                "thumbnail_url": thumbnail_url,
                "source": "PEXELS",
                "source_url": source_url if _valid_image_url(source_url) else None,
                "credit": item.get("photographer"),
            }
        )
        if len(results) >= limit:
            break

    return results


def search_product_images(
    query: str,
    per_page: int = 12,
) -> list[dict[str, str | int | None]]:
    clean_query = query.strip()
    limit = min(max(per_page, 1), 20)

    if not settings.brave_search_api_key and not settings.pexels_api_key:
        logger.warning("Product image search not configured: no provider API key is available.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Product image search is not configured. Set "
                "BRAVE_SEARCH_API_KEY or PEXELS_API_KEY."
            ),
        )

    if settings.brave_search_api_key and settings.brave_images_url:
        try:
            results = _search_brave(clean_query, limit)
            if results:
                logger.info(
                    "Product image search provider=BRAVE query=%r results=%d",
                    clean_query,
                    len(results),
                )
                return results
            logger.warning(
                "Product image search provider=BRAVE returned no usable images "
                "for query=%r; falling back to PEXELS",
                clean_query,
            )
        except requests.RequestException as exc:
            logger.warning(
                "Product image search provider=BRAVE failed for query=%r "
                "error=%s; falling back to PEXELS",
                clean_query,
                exc,
            )

    if settings.pexels_api_key and settings.pexels_images_url:
        try:
            results = _search_pexels(clean_query, limit)
            logger.info(
                "Product image search provider=PEXELS query=%r results=%d",
                clean_query,
                len(results),
            )
            return results
        except requests.RequestException as exc:
            logger.warning(
                "Product image search provider=PEXELS failed for query=%r error=%s",
                clean_query,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not retrieve product images.",
            ) from exc

    logger.warning(
        "Product image search has no usable fallback provider configured for query=%r",
        clean_query,
    )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Product image search is not configured. Set the provider API key "
            "and URL environment variables."
        ),
    )
