from datetime import UTC, datetime

from app.ingestion.fia_documents import classify_fia_document, parse_fia_decision_documents

HTML = """
<html><body>
  <section>
    <h3>Austrian Grand Prix</h3>
    <ul>
      <li>
        <a href="/sites/default/files/doc-14.pdf">
          Doc 14 - Car Presentation Submissions
        </a>
        <span>Published on 26.06.26 11:00 CEST</span>
      </li>
      <li>
        <a href="/sites/default/files/doc-40.pdf">
          Doc 40 - Parts and Parameters been replaced and or changed during Parc Fermé
        </a>
        <span>Published on 28.06.26 13:51 CEST</span>
      </li>
      <li>
        <a href="/sites/default/files/doc-45.pdf">
          Doc 45 - Decision - Car 23 - Alleged yellow flag infringement
        </a>
        <span>Published on 28.06.26 17:00 CEST</span>
      </li>
    </ul>
  </section>
  <section>
    <h3>Spanish Grand Prix</h3>
    <a href="/sites/default/files/doc-67.pdf">
      Doc 67 - Infringement - Car 55 - Causing a Collision with Car 14
      Published on 13.09.26 16:13 CEST
    </a>
  </section>
</body></html>
"""


def test_parser_extracts_event_documents_links_and_publication_times() -> None:
    documents = parse_fia_decision_documents(
        HTML,
        base_url="https://www.fia.com/documents/season/2026",
        known_event_names={"Austrian Grand Prix", "Spanish Grand Prix"},
    )

    assert len(documents) == 4
    first = documents[0]
    assert first.event_name == "Austrian Grand Prix"
    assert first.document_number == 14
    assert first.document_type == "car_presentation"
    assert first.document_url == "https://www.fia.com/sites/default/files/doc-14.pdf"
    assert first.published_at == datetime(2026, 6, 26, 9, 0, tzinfo=UTC)

    madrid = documents[-1]
    assert madrid.event_name == "Spanish Grand Prix"
    assert madrid.document_number == 67
    assert madrid.document_type == "stewards"
    assert madrid.published_at == datetime(2026, 9, 13, 14, 13, tzinfo=UTC)


def test_document_classifier_keeps_high_signal_types_distinct() -> None:
    assert classify_fia_document("Car Presentation Submissions") == "car_presentation"
    assert classify_fia_document("Parts and parameters changed during Parc Ferme") == "parc_ferme"
    assert classify_fia_document("Final Race Classification") == "classification"
    assert classify_fia_document("New PU Elements for this Competition") == "power_unit"
    assert classify_fia_document("Race Director's Competition Notes V3") == "race_director"


def test_parser_ignores_unknown_event_sections() -> None:
    documents = parse_fia_decision_documents(
        "<h3>WEC</h3><a href='/wec.pdf'>Doc 1 - Entry List</a> "
        "Published on 01.01.26 10:00 CET",
        base_url="https://www.fia.com/",
        known_event_names={"Austrian Grand Prix"},
    )
    assert documents == []
