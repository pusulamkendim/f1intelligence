from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.ingestion.openf1_telemetry import parse_laps, parse_locations, parse_positions, parse_stints

OPENF1_BASE_URL = "https://api.openf1.org/v1"
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class OpenF1Meeting:
    meeting_key: int
    year: int
    meeting_name: str
    meeting_official_name: str | None
    circuit_key: int | None
    circuit_short_name: str | None
    country_name: str | None
    location: str | None
    date_start: datetime
    date_end: datetime
    gmt_offset: str | None
    is_cancelled: bool


@dataclass(frozen=True)
class OpenF1Session:
    session_key: int
    meeting_key: int
    year: int
    session_name: str
    session_type: str | None
    session_code: str
    circuit_key: int | None
    circuit_short_name: str | None
    country_name: str | None
    location: str | None
    date_start: datetime
    date_end: datetime | None
    gmt_offset: str | None
    is_cancelled: bool


@dataclass(frozen=True)
class OpenF1Driver:
    session_key: int
    meeting_key: int
    driver_number: int
    broadcast_name: str | None
    first_name: str | None
    last_name: str | None
    full_name: str | None
    name_acronym: str | None
    team_name: str | None
    team_colour: str | None
    headshot_url: str | None


@dataclass(frozen=True)
class OpenF1SessionResult:
    session_key: int
    meeting_key: int
    driver_number: int
    position: int | None
    dnf: bool
    dns: bool
    dsq: bool
    number_of_laps: int | None
    duration_seconds: float | None
    q1_seconds: float | None
    q2_seconds: float | None
    q3_seconds: float | None
    gap_to_leader_seconds: float | None
    gap_to_leader_text: str | None
    q1_gap_seconds: float | None
    q2_gap_seconds: float | None
    q3_gap_seconds: float | None


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def normalize_session_code(name: str) -> str | None:
    mapping = {"practice 1": "practice_1", "practice 2": "practice_2", "practice 3": "practice_3", "sprint qualifying": "sprint_qualifying", "sprint shootout": "sprint_qualifying", "sprint": "sprint", "qualifying": "qualifying", "race": "race"}
    return mapping.get(name.strip().casefold())


def _scalar_and_qualifying(value: Any) -> tuple[float | None, float | None, float | None, float | None]:
    if isinstance(value, list):
        values = [float(item) if isinstance(item, (int, float)) else None for item in value[:3]]
        values.extend([None] * (3 - len(values)))
        return None, values[0], values[1], values[2]
    if isinstance(value, (int, float)):
        return float(value), None, None, None
    return None, None, None, None


def _gap_values(value: Any) -> tuple[float | None, str | None, float | None, float | None, float | None]:
    if isinstance(value, list):
        parsed = [float(item) if isinstance(item, (int, float)) else None for item in value[:3]]
        parsed.extend([None] * (3 - len(parsed)))
        return None, None, parsed[0], parsed[1], parsed[2]
    if isinstance(value, (int, float)):
        return float(value), None, None, None, None
    if isinstance(value, str):
        return None, value, None, None, None
    return None, None, None, None, None


def parse_meetings(payload: list[dict[str, Any]]) -> list[OpenF1Meeting]:
    return [OpenF1Meeting(int(r["meeting_key"]), int(r["year"]), r["meeting_name"], r.get("meeting_official_name"), int(r["circuit_key"]) if r.get("circuit_key") is not None else None, r.get("circuit_short_name"), r.get("country_name"), r.get("location"), _dt(r["date_start"]), _dt(r["date_end"]), r.get("gmt_offset"), bool(r.get("is_cancelled", False))) for r in payload if "Grand Prix" in r.get("meeting_name", "")]


def parse_sessions(payload: list[dict[str, Any]]) -> list[OpenF1Session]:
    parsed = []
    for r in payload:
        code = normalize_session_code(r.get("session_name", ""))
        if code:
            parsed.append(OpenF1Session(int(r["session_key"]), int(r["meeting_key"]), int(r["year"]), r["session_name"], r.get("session_type"), code, int(r["circuit_key"]) if r.get("circuit_key") is not None else None, r.get("circuit_short_name"), r.get("country_name"), r.get("location"), _dt(r["date_start"]), _dt(r["date_end"]) if r.get("date_end") else None, r.get("gmt_offset"), bool(r.get("is_cancelled", False))))
    return parsed


def parse_drivers(payload: list[dict[str, Any]]) -> list[OpenF1Driver]:
    return [OpenF1Driver(int(r["session_key"]), int(r["meeting_key"]), int(r["driver_number"]), r.get("broadcast_name"), r.get("first_name"), r.get("last_name"), r.get("full_name"), r.get("name_acronym"), r.get("team_name"), r.get("team_colour"), r.get("headshot_url")) for r in payload if r.get("driver_number") is not None]


def parse_session_results(payload: list[dict[str, Any]]) -> list[OpenF1SessionResult]:
    parsed = []
    for r in payload:
        duration, q1, q2, q3 = _scalar_and_qualifying(r.get("duration"))
        gap, gap_text, q1_gap, q2_gap, q3_gap = _gap_values(r.get("gap_to_leader"))
        parsed.append(OpenF1SessionResult(int(r["session_key"]), int(r["meeting_key"]), int(r["driver_number"]), int(r["position"]) if r.get("position") is not None else None, bool(r.get("dnf", False)), bool(r.get("dns", False)), bool(r.get("dsq", False)), int(r["number_of_laps"]) if r.get("number_of_laps") is not None else None, duration, q1, q2, q3, gap, gap_text, q1_gap, q2_gap, q3_gap))
    return parsed


class OpenF1Client:
    def __init__(self, client: httpx.AsyncClient, *, base_url: str = OPENF1_BASE_URL, min_interval_seconds: float = 0.4, retries: int = 4, retry_backoff_seconds: float = 1.0) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.min_interval_seconds = min_interval_seconds
        self.retries = retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self._last_request_at = 0.0

    async def _pace(self) -> None:
        remaining = self.min_interval_seconds - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            await asyncio.sleep(remaining)

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        raw = response.headers.get("Retry-After")
        if not raw:
            return None
        try:
            return max(0.0, float(raw))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(raw)
                return max(0.0, (parsed - datetime.now(parsed.tzinfo or UTC)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    async def _get(self, endpoint: str, **params: Any) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            await self._pace()
            try:
                response = await self.client.get(f"{self.base_url}/{endpoint.lstrip('/')}", params=params)
                self._last_request_at = time.monotonic()
                if response.status_code not in RETRYABLE_STATUSES:
                    response.raise_for_status()
                    return response.json()
                last_error = httpx.HTTPStatusError(f"retryable OpenF1 HTTP {response.status_code}", request=response.request, response=response)
                delay = self._retry_after(response)
            except httpx.TransportError as exc:
                self._last_request_at = time.monotonic()
                last_error = exc
                delay = None
            if attempt == self.retries - 1:
                break
            await asyncio.sleep(delay if delay is not None else self.retry_backoff_seconds * (2**attempt))
        assert last_error is not None
        raise last_error

    async def meetings(self, year: int):
        return parse_meetings(await self._get("meetings", year=year))

    async def sessions(self, year: int):
        return parse_sessions(await self._get("sessions", year=year))

    async def drivers(self, session_key: int):
        return parse_drivers(await self._get("drivers", session_key=session_key))

    async def session_results(self, session_key: int):
        return parse_session_results(await self._get("session_result", session_key=session_key))

    async def laps(self, session_key: int):
        return parse_laps(await self._get("laps", session_key=session_key))

    async def stints(self, session_key: int):
        return parse_stints(await self._get("stints", session_key=session_key))

    async def positions(self, session_key: int):
        return parse_positions(await self._get("position", session_key=session_key))

    async def locations(self, session_key: int, *, sample_interval_ms: int = 1000):
        return parse_locations(
            await self._get("location", session_key=session_key),
            sample_interval_ms=sample_interval_ms,
        )
