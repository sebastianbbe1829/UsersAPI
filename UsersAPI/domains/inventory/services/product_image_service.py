import os

import requests
from fastapi import HTTPException, status


def search_product_images(query: str, per_page: int = 12) -> list[dict[str, str | int | None]]:
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product image search is not configured. Set PEXELS_API_KEY.",
        )

    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
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
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve product images.",
        ) from exc

    payload = response.json()
    return [
        {
            "id": photo.get("id"),
            "url": photo.get("src", {}).get("medium"),
            "source_url": photo.get("url"),
            "credit": photo.get("photographer"),
            "alt": photo.get("alt"),
        }
        for photo in payload.get("photos", [])
        if photo.get("src", {}).get("medium")
    ]
