from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
from urllib.parse import urljoin

from app.ingestion.entity_matcher import normalize_entity_text

_DOC_RE = re.compile(r"^(?P<recalled>Recalled\s*-\s*)?Doc\s+(?P<number>\d+)\s*-\s*(?P<title>.+)$", re.I)
_PUBLISHED_RE = re.compile(
    r"Published\s+on\s+(?P<date>\d{2}\.\d{2}\.\d{2})\s+"
    r"(?P<time>\d{2}:\d{2})\s+(?P<zone>CET|CEST)",
    re.I,
)


@dataclass(frozen=True)
class FiaDecisionDocument:
    event_name: str
    document_number: int
    title: str
    document_type: str
    document_url: str
    published_at: datetime | None
    published_label: str | None
    recalled: bool
    external_id: str


def classify_fia_document(title: str) -> str:
    normalized = normalize_entity_text(title)
    if "car presentation submissions" in normalized:
        return "car_presentation"
    if "parts and parameters" in normalized or "parc ferme" in normalized:
        return "parc_ferme"
    if normalized.startswith(("decision ", "infringement ", "summons ")):
        return "stewards"
    if "starting grid" in normalized:
        return "starting_grid"
    if "classification" in normalized:
        return "classification"
    if "scrutineering" in normalized:
        return "scrutineering"
    if "pu element" in normalized or "power unit" in normalized:
        return "power_unit"
    if "race director" in normalized:
        return "race_director"
    if "entry list" in normalized:
        return "entry_list"
    if "pirelli" in normalized:
        return "tyre"
    return "other"


def _parse_published(value: str) -> datetime | None:
    match = _PUBLISHED_RE.search(value)
    if not match:
        return None

    local = datetime.strptime(
        f"{match.group('date')} {match.group('time')}",
        "%d.%m.%y %H:%M",
    )
    offset = timedelta(hours=2 if match.group("zone").upper() == "CEST" else 1)
    return local.replace(tzinfo=timezone(offset)).astimezone(UTC)


class _DecisionDocumentParser(HTMLParser):
    def __init__(self, *, base_url: str, known_event_names: set[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.event_lookup = {
            normalize_entity_text(name): name for name in known_event_names if name.strip()
        }
        self.current_event: str | None = None
        self.anchor_href: str | None = None
        self.anchor_parts: list[str] = []
        self.pending: dict[str, object] | None = None
        self.pending_tail: list[str] = []
        self.documents: list[FiaDecisionDocument] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        if self.pending is not None:
            self._finalize_pending()
        self.anchor_href = dict(attrs).get("href")
        self.anchor_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "a" or self.anchor_href is None:
            return
        self._capture_anchor()
        self.anchor_href = None
        self.anchor_parts = []

    def handle_data(self, data: str) -> None:
        if self.anchor_href is not None:
            self.anchor_parts.append(data)
            return

        stripped = " ".join(data.split())
        if not stripped:
            return

        normalized = normalize_entity_text(stripped)
        if normalized in self.event_lookup:
            if self.pending is not None:
                self._finalize_pending()
            self.current_event = self.event_lookup[normalized]
            return

        if self.pending is not None:
            self.pending_tail.append(stripped)
            joined = " ".join(self.pending_tail)
            if _PUBLISHED_RE.search(joined):
                self.pending["published_label"] = _PUBLISHED_RE.search(joined).group(0)  # type: ignore[union-attr]
                self.pending["published_at"] = _parse_published(joined)
                self._finalize_pending()

    def close(self) -> None:
        super().close()
        if self.pending is not None:
            self._finalize_pending()

    def _capture_anchor(self) -> None:
        if self.current_event is None or not self.anchor_href:
            return

        text_value = " ".join(" ".join(self.anchor_parts).split())
        published_match = _PUBLISHED_RE.search(text_value)
        published_label = published_match.group(0) if published_match else None
        title_text = text_value[: published_match.start()].strip() if published_match else text_value
        doc_match = _DOC_RE.match(title_text)
        if not doc_match:
            return

        document_url = urljoin(self.base_url, self.anchor_href)
        title = doc_match.group("title").strip()
        self.pending = {
            "event_name": self.current_event,
            "document_number": int(doc_match.group("number")),
            "title": title,
            "document_type": classify_fia_document(title),
            "document_url": document_url,
            "published_at": _parse_published(published_label or ""),
            "published_label": published_label,
            "recalled": bool(doc_match.group("recalled")),
        }
        self.pending_tail = []

        if published_label:
            self._finalize_pending()

    def _finalize_pending(self) -> None:
        if self.pending is None:
            return

        event_name = str(self.pending["event_name"])
        document_number = int(self.pending["document_number"])
        title = str(self.pending["title"])
        document_url = str(self.pending["document_url"])
        external_id = sha256(
            f"{event_name}|{document_number}|{document_url}".encode()
        ).hexdigest()

        self.documents.append(
            FiaDecisionDocument(
                event_name=event_name,
                document_number=document_number,
                title=title,
                document_type=str(self.pending["document_type"]),
                document_url=document_url,
                published_at=self.pending["published_at"]  # type: ignore[arg-type]
                if isinstance(self.pending["published_at"], datetime)
                else None,
                published_label=str(self.pending["published_label"])
                if self.pending["published_label"]
                else None,
                recalled=bool(self.pending["recalled"]),
                external_id=external_id,
            )
        )
        self.pending = None
        self.pending_tail = []


def parse_fia_decision_documents(
    html_text: str,
    *,
    base_url: str,
    known_event_names: set[str],
) -> list[FiaDecisionDocument]:
    parser = _DecisionDocumentParser(base_url=base_url, known_event_names=known_event_names)
    parser.feed(html_text)
    parser.close()
    return parser.documents
