from datetime import UTC, datetime
from uuid import uuid4

from app.ingestion.fia_rss import (
    FeedItem,
    MatchTerm,
    StoryRule,
    choose_story,
    parse_fia_rss,
    score_item,
)

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>FIA Press Releases</title>
    <item>
      <title>2026 FIA Formula One World Championship calendar update</title>
      <link>https://www.fia.com/news/example-calendar-update</link>
      <guid>fia-example-1</guid>
      <pubDate>Tue, 16 Sep 2026 12:00:00 +0000</pubDate>
      <category>Formula 1</category>
      <category>Sport</category>
    </item>
    <item>
      <title>F1 - 2026 Italian Grand Prix - Thursday Press Conference Transcript</title>
      <link>https://www.fia.com/news/example-transcript</link>
      <guid>fia-example-2</guid>
      <pubDate>Thu, 03 Sep 2026 12:00:00 +0000</pubDate>
      <category>Formula 1</category>
    </item>
  </channel>
</rss>
"""


def rule() -> StoryRule:
    return StoryRule(
        story_id=uuid4(),
        slug="fia-2026-sporting-decisions",
        min_score=3,
        terms=(
            MatchTerm("2026 FIA Formula One World Championship", 3),
            MatchTerm("Formula 1", 1),
            MatchTerm("calendar", 2),
            MatchTerm("decision", 2),
        ),
    )


def test_parse_fia_rss_extracts_source_metadata() -> None:
    items = parse_fia_rss(RSS)

    assert len(items) == 2
    assert items[0].external_id == "fia-example-1"
    assert items[0].url == "https://www.fia.com/news/example-calendar-update"
    assert items[0].published_at == datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    assert items[0].categories == ("Formula 1", "Sport")


def test_matcher_attaches_specific_official_update() -> None:
    item = parse_fia_rss(RSS)[0]
    story_rule = rule()

    assert score_item(item, story_rule) == 6
    match = choose_story(item, [story_rule])
    assert match.status == "matched"
    assert match.story_slug == "fia-2026-sporting-decisions"


def test_matcher_rejects_generic_press_conference_transcript() -> None:
    item = parse_fia_rss(RSS)[1]
    match = choose_story(item, [rule()])

    assert match.status == "unmatched"
    assert match.story_id is None


def test_matcher_marks_equal_top_scores_ambiguous() -> None:
    item = FeedItem(
        external_id="x",
        title="Formula 1 calendar decision",
        url=None,
        published_at=None,
        categories=(),
    )
    first = StoryRule(
        story_id=uuid4(),
        slug="first",
        min_score=2,
        terms=(MatchTerm("calendar", 2),),
    )
    second = StoryRule(
        story_id=uuid4(),
        slug="second",
        min_score=2,
        terms=(MatchTerm("decision", 2),),
    )

    match = choose_story(item, [first, second])
    assert match.status == "ambiguous"
    assert match.story_id is None
