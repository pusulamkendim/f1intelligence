from datetime import UTC, datetime

from app.ingestion.editorial_sources import (
    EditorialSource,
    discover_listing_urls,
    parse_article_html,
    parse_feed,
)
from app.ingestion.source_registry import (
    ALL_SOURCES,
    DISABLED_SOURCE_REASONS,
    DISABLED_SOURCES,
    SOURCE_BY_KEY,
    SOURCES,
)


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


def test_generic_article_parser_prefers_document_title_over_malformed_h1() -> None:
    source = EditorialSource(
        key="team_alpine",
        provider="alpinef1.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.alpinef1.com/news",
    )
    html = """
    <html lang="en">
      <head>
        <title>Mike Elliott joins as Chief Technical Officer</title>
        <link rel="canonical" href="https://www.alpinef1.com/news/mike-elliott-joins-as-chief-technical-officer" />
      </head>
      <body><h1>BWT Alpine Formula One Team today announces that Mike Elliott is joining the team as Chief Technical Officer and will lead the technical organisation at Enstone.</h1></body>
    </html>
    """

    item = parse_article_html(
        html,
        requested_url="https://www.alpinef1.com/news/mike-elliott-joins-as-chief-technical-officer",
        source=source,
    )

    assert item.title == "Mike Elliott joins as Chief Technical Officer"
    assert item.raw_metadata["title_fallback"] == "document_title"


def test_registry_covers_editorial_team_and_community_classes() -> None:
    keys = [source.key for source in ALL_SOURCES]
    assert len(keys) == len(set(keys))
    assert set(source.source_class for source in SOURCES) == {
        "independent_editorial",
        "first_party_team",
        "community_signal",
    }
    team_sources = [
        source for source in ALL_SOURCES if source.source_class == "first_party_team"
    ]
    assert len(team_sources) == 11
    assert len({source.team_slug for source in team_sources}) == 11
    assert all(source.team_slug for source in team_sources)
    assert SOURCE_BY_KEY["autosport_f1"].mode == "rss"
    assert SOURCE_BY_KEY["reddit_formula1"].source_class == "community_signal"


def test_live_registry_corrections_filter_known_noise() -> None:
    mclaren = SOURCE_BY_KEY["team_mclaren"]
    assert discover_listing_urls(
        '<a href="/racing/formula-1/standings">Standings</a>'
        '<a href="/racing/formula-1/f1-academy">F1 Academy</a>'
        '<a href="/racing/formula-1/2026/schedule/">Schedule</a>'
        '<a href="/racing/formula-1/2026/azerbaijan-grand-prix">GP landing</a>'
        '<a href="/racing/formula-1/2026/spanish-grand-prix/race-report/">Race</a>',
        mclaren,
    ) == ["https://www.mclaren.com/racing/formula-1/2026/spanish-grand-prix/race-report"]

    red_bull = SOURCE_BY_KEY["team_red_bull"]
    assert discover_listing_urls(
        '<a href="/int-en/races">Calendar</a>'
        '<a href="/int-en/my-paddock">Paddock</a>'
        '<a href="/int-en/newsletter">Newsletter</a>'
        '<a href="/int-en/races/spanish-grand-prix/race-report">Race story</a>'
        '<a href="/int-en/madrid-on-rails-2026">Story</a>',
        red_bull,
    ) == [
        "https://www.redbullracing.com/int-en/races/spanish-grand-prix/race-report",
        "https://www.redbullracing.com/int-en/madrid-on-rails-2026",
    ]

    racing_bulls = SOURCE_BY_KEY["team_racing_bulls"]
    assert discover_listing_urls(
        '<a href="/int-en/the-garage">Garage</a>'
        '<a href="/int-en/creator-platform">Creator platform</a>'
        '<a href="/int-en/2026-driver-line-up-announcement">Story</a>',
        racing_bulls,
    ) == ["https://www.visacashapprb.com/int-en/2026-driver-line-up-announcement"]

    williams = SOURCE_BY_KEY["team_williams"]
    assert discover_listing_urls(
        '<a href="/articles/11111111-1111-1111-1111-111111111111/'
        'williams-f1-team-academy-driver-formula-3-2027">Academy</a>'
        '<a href="/articles/22222222-2222-2222-2222-222222222222/'
        'spanish-grand-prix-race-report">Race</a>',
        williams,
    ) == [
        "https://www.williamsf1.com/articles/22222222-2222-2222-2222-222222222222/"
        "spanish-grand-prix-race-report"
    ]

    aston = SOURCE_BY_KEY["team_aston_martin"]
    assert discover_listing_urls(
        '<a href="/en-GB/news/feature">Feature category</a>'
        '<a href="/en-GB/news/feature/some-assembly-required">Feature article</a>'
        '<a href="/en-GB/news/announcement/f1-2027-calendar-revealed">Announcement article</a>',
        aston,
    ) == [
        "https://www.astonmartinf1.com/en-GB/news/feature/some-assembly-required",
        "https://www.astonmartinf1.com/en-GB/news/announcement/f1-2027-calendar-revealed",
    ]


def test_failed_live_endpoints_are_explicitly_disabled() -> None:
    disabled_keys = {source.key for source in DISABLED_SOURCES}
    assert disabled_keys == {"team_ferrari", "team_cadillac", "reddit_f1technical"}
    assert "403" in DISABLED_SOURCE_REASONS["team_ferrari"]
    assert "403" in DISABLED_SOURCE_REASONS["team_cadillac"]
    assert "429" in DISABLED_SOURCE_REASONS["reddit_f1technical"]
    assert SOURCE_BY_KEY["team_red_bull"].discovery_url == "https://www.redbullracing.com/int-en"
    assert SOURCE_BY_KEY["team_racing_bulls"].provider == "visacashapprb.com"
    assert SOURCE_BY_KEY["team_audi"].discovery_url.endswith("audi-formula-racing-gmbh-17953")
