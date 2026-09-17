from datetime import UTC, datetime

from app.ingestion.editorial_sources import (
    EditorialSource,
    discover_listing_urls,
    parse_article_html,
    parse_feed,
)
from app.ingestion.source_registry import SOURCE_BY_KEY, SOURCES


def test_rss_parser_extracts_metadata_without_full_article_fetch() -> None:
    source = EditorialSource(
        key="test_rss",
        provider="example.com",
        source_class="independent_editorial",
        mode="rss",
        discovery_url="https://example.com/f1.xml",
    )
    xml = """
    <rss><channel><item>
      <guid>story-123</guid>
      <title>Verstappen explains Red Bull update</title>
      <link>https://example.com/f1/story?utm_source=rss</link>
      <pubDate>Thu, 17 Sep 2026 12:00:00 GMT</pubDate>
      <description><![CDATA[<p>Red Bull brought a revised floor to Madrid.</p>]]></description>
      <category>Formula 1</category>
    </item></channel></rss>
    """

    item = parse_feed(xml, source)[0]

    assert item.external_id == "story-123"
    assert item.canonical_url == "https://example.com/f1/story"
    assert item.summary == "Red Bull brought a revised floor to Madrid."
    assert item.section == "Formula 1"
    assert item.published_at == datetime(2026, 9, 17, 12, 0, tzinfo=UTC)


def test_atom_parser_supports_reddit_style_entries() -> None:
    source = EditorialSource(
        key="reddit_test",
        provider="reddit:r/formula1",
        source_class="community_signal",
        mode="rss",
        discovery_url="https://www.reddit.com/r/formula1/.rss",
    )
    xml = """
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>t3_example</id>
        <title>Spanish GP discussion</title>
        <link href="https://www.reddit.com/r/formula1/comments/example/spanish_gp/" />
        <updated>2026-09-17T12:30:00+00:00</updated>
        <content type="html">&lt;p&gt;Discussion about the race.&lt;/p&gt;</content>
      </entry>
    </feed>
    """

    item = parse_feed(xml, source)[0]

    assert item.external_id == "t3_example"
    assert item.title == "Spanish GP discussion"
    assert item.summary == "Discussion about the race."


def test_listing_discovery_is_host_and_path_bounded() -> None:
    source = EditorialSource(
        key="team_test",
        provider="team.example",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://team.example/news",
        allowed_hosts=("team.example",),
        article_path_pattern=r"^/news/.+",
    )
    html = """
    <a href="/news/spanish-gp-report">Report</a>
    <a href="https://team.example/news/technical-update?foo=1">Technical</a>
    <a href="/drivers/max">Driver</a>
    <a href="https://external.example/news/not-ours">External</a>
    """

    assert discover_listing_urls(html, source) == [
        "https://team.example/news/spanish-gp-report",
        "https://team.example/news/technical-update",
    ]


def test_generic_article_parser_prefers_json_ld() -> None:
    source = EditorialSource(
        key="team_test",
        provider="team.example",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://team.example/news",
    )
    html = """
    <html lang="en"><head>
      <link rel="canonical" href="https://team.example/news/update" />
      <script type="application/ld+json">
      {
        "@type": "NewsArticle",
        "headline": "Technical update for Madrid",
        "description": "The team explains its revised floor.",
        "datePublished": "2026-09-17T10:00:00Z",
        "articleSection": "Technical",
        "author": {"name": "Team Media"}
      }
      </script>
    </head></html>
    """

    item = parse_article_html(html, requested_url="https://team.example/news/old", source=source)

    assert item.canonical_url == "https://team.example/news/update"
    assert item.title == "Technical update for Madrid"
    assert item.summary == "The team explains its revised floor."
    assert item.section == "Technical"
    assert item.author == "Team Media"


def test_registry_covers_editorial_team_and_community_classes() -> None:
    keys = [source.key for source in SOURCES]
    assert len(keys) == len(set(keys))
    assert set(source.source_class for source in SOURCES) == {
        "independent_editorial",
        "first_party_team",
        "community_signal",
    }
    team_sources = [source for source in SOURCES if source.source_class == "first_party_team"]
    assert len(team_sources) == 11
    assert all(source.team_slug for source in team_sources)
    assert SOURCE_BY_KEY["autosport_f1"].mode == "rss"
    assert SOURCE_BY_KEY["reddit_formula1"].source_class == "community_signal"
