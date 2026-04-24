from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp


class ApiError(Exception):
    pass


@dataclass
class NewsItem:
    title: str
    url: str
    score: int


@dataclass
class WeatherReport:
    city: str
    temperature_c: float
    wind_kmh: float
    weather_code: int
    temp_max_c: float
    temp_min_c: float


class PublicApiClient:
    def __init__(self, timeout_seconds: int = 10, retries: int = 2) -> None:
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    async def _get_json(self, url: str, params: Optional[dict[str, Any]] = None) -> Any:
        last_error: Optional[Exception] = None
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

        for attempt in range(self.retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 429:
                            raise ApiError("Rate limit reached. Please try again shortly.")
                        if response.status >= 500:
                            raise ApiError("Service is temporarily unavailable.")
                        if response.status >= 400:
                            detail = await response.text()
                            raise ApiError(
                                f"Request failed with status {response.status}: {detail[:120]}"
                            )
                        return await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError, ApiError) as exc:
                last_error = exc
                if attempt < self.retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                break

        raise ApiError(f"Unable to reach external API: {last_error}")

    async def get_top_tech_news(self, limit: int = 5) -> list[NewsItem]:
        ids = await self._get_json("https://hacker-news.firebaseio.com/v0/topstories.json")
        if not isinstance(ids, list) or not ids:
            raise ApiError("No stories were returned by the news API.")

        candidate_ids = ids[: max(limit * 3, 15)]
        tasks = [
            self._get_json(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            for story_id in candidate_ids
        ]
        raw_items = await asyncio.gather(*tasks, return_exceptions=True)

        stories: list[NewsItem] = []
        for item in raw_items:
            if isinstance(item, Exception):
                continue
            if not isinstance(item, dict):
                continue
            if item.get("type") != "story":
                continue
            title = str(item.get("title", "Untitled"))
            url = str(item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}")
            score = int(item.get("score", 0))
            stories.append(NewsItem(title=title, url=url, score=score))
            if len(stories) >= limit:
                break

        if not stories:
            raise ApiError("Could not find any valid news stories right now.")

        return stories

    async def get_weather(self, city: str) -> WeatherReport:
        geo = await self._get_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )

        results = geo.get("results") if isinstance(geo, dict) else None
        if not results:
            raise ApiError(f"No city match found for '{city}'.")

        location = results[0]
        latitude = location.get("latitude")
        longitude = location.get("longitude")
        location_name = location.get("name", city)

        forecast = await self._get_json(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,wind_speed_10m,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "UTC",
                "forecast_days": 1,
            },
        )

        current = forecast.get("current", {}) if isinstance(forecast, dict) else {}
        daily = forecast.get("daily", {}) if isinstance(forecast, dict) else {}
        max_list = daily.get("temperature_2m_max") or [0]
        min_list = daily.get("temperature_2m_min") or [0]

        return WeatherReport(
            city=str(location_name),
            temperature_c=float(current.get("temperature_2m", 0.0)),
            wind_kmh=float(current.get("wind_speed_10m", 0.0)),
            weather_code=int(current.get("weather_code", 0)),
            temp_max_c=float(max_list[0]),
            temp_min_c=float(min_list[0]),
        )
