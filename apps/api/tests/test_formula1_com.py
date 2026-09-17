from datetime import UTC, datetime

from app.ingestion.formula1_com import (
    MAX_BODY_EXCERPT_CHARS,
    Formula1Article,
    discover_formula1_article_urls,
    is_formula1_relevant_article,
    parse_formula1_article,
)
from app.ingestion.run_formula1 import RIGHTS_POLICY, SOURCE_CLASS, article_to_source_item


def test_discovery_returns_only_canonical_formula1_article_links() -> None:
    html = """
    <html><body>
      <a href="/en/latest/article/verstappen-explains-red-bull-update.ABC123">One</a>
      <a href="https://www.formula1.com/en/latest/article/another-story.DEF456?foo=bar">Two</a>
      <a href="/en/latest/tags/red-bull">Tag</a>
      <a href="/en/video/example">Video</a>
      <a href="https://example.com/en/latest/article/not-f1.XYZ999">External</a>
      <a href="/en/latest/article/verstappen-explains-red-bull-update.ABC123">Duplicate</a>
    </body></html>
    """

    urls = discover_formula1_article_urls(html, base_url="https://www.formula1.com/en/latest")

    assert urls == [
        "https://www.formula1.com/en/latest/article/verstappen-explains-red-bull-update.ABC123",
        "https://www.formula1.com/en/latest/article/another-story.DEF456",
    ]


def test_article_parser_prefers_json_ld_and_bounds_body_excerpt() -> None:
    body = "x" * (MAX_BODY_EXCERPT_CHARS + 200)
    html = f"""
    <html lang="en">
      <head>
        <link rel="canonical" href="https://www.formula1.com/en/latest/article/test-story.ABC123" />
        <meta property="og:title" content="Fallback title" />
        <script type="application/ld+json">
        {{
          "@context": "https://schema.org",
          "@type": "NewsArticle",
          "headline": "Verstappen explains Red Bull balance issue",
          "description": "The team explains what changed after qualifying.",
          "datePublished": "2026-09-17T14:30:00Z",
          "articleSection": "Technical",
          "author": {{"@type": "Person", "name": "F1 Staff"}},
          "articleBody": "{body}"
        }}
        </script>
      </head>
    </html>
    """

    article = parse_formula1_article(
        html,
        requested_url="https://www.formula1.com/en/latest/article/ignored.OLD111",
    )

    assert article.external_id == "ABC123"
    assert article.title == "Verstappen explains Red Bull balance issue"
    assert article.description == "The team explains what changed after qualifying."
    assert article.published_at == datetime(2026, 9, 17, 14, 30, tzinfo=UTC)
    assert article.section == "Technical"
    assert article.author == "F1 Staff"
    assert article.body_excerpt is not None
    assert len(article.body_excerpt) == MAX_BODY_EXCERPT_CHARS


def test_article_parser_falls_back_to_open_graph_metadata() -> None:
    html = """
    <html lang="en-GB"><head>
      <meta property="og:url" content="https://www.formula1.com/en/latest/article/fallback-story.XYZ789" />
      <meta property="og:title" content="Hamilton reacts after Madrid race" />
      <meta property="og:description" content="Hamilton gives his reaction after the race." />
      <meta property="article:published_time" content="2026-09-13T17:05:00+00:00" />
      <meta property="article:section" content="News" />
      <meta name="author" content="Formula 1" />
    </head></html>
    """

    article = parse_formula1_article(
        html,
        requested_url="https://www.formula1.com/en/latest/article/fallback-story.XYZ789",
    )

    assert article.external_id == "XYZ789"
    assert article.title == "Hamilton reacts after Madrid race"
    assert article.description == "Hamilton gives his reaction after the race."
    assert article.language == "en-GB"
    assert article.section == "News"
    assert article.author == "Formula 1"


def test_formula1_relevance_filter_drops_feeder_series_sections() -> None:
    base = dict(
        external_id="id",
        canonical_url="https://www.formula1.com/en/latest/article/example.ID",
        title="Example",
    )

    assert not is_formula1_relevant_article(Formula1Article(**base, section="F2"))
    assert not is_formula1_relevant_article(Formula1Article(**base, section="F3"))
    assert not is_formula1_relevant_article(Formula1Article(**base, section="F1 Academy"))
    assert is_formula1_relevant_article(Formula1Article(**base, section="Technical"))
    assert is_formula1_relevant_article(Formula1Article(**base, section=None))


def test_formula1_article_maps_to_source_item_contract() -> None:
    html = """
    <html><head>
      <meta property="og:url" content="https://www.formula1.com/en/latest/article/red-bull-story.RB2026" />
      <meta property="og:title" content="Red Bull assess their latest upgrade" />
      <meta property="og:description" content="The team reviews the package after qualifying." />
      <meta property="article:published_time" content="2026-09-17T12:00:00Z" />
    </head></html>
    """
    article = parse_formula1_article(
        html,
        requested_url="https://www.formula1.com/en/latest/article/red-bull-story.RB2026",
    )

    item = article_to_source_item(article)

    assert item.provider == "formula1.com"
    assert item.source_class == SOURCE_CLASS
    assert item.source_type == "article"
    assert item.standfirst == "The team reviews the package after qualifying."
    assert item.rights_policy == RIGHTS_POLICY
    assert item.content_hash == article.content_hash
