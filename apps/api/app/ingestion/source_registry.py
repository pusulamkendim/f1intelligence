from __future__ import annotations

from app.ingestion.editorial_sources import EditorialSource

# Active sources are expected to be fetchable by a normal server-side HTTP client.
# Sites that explicitly challenge/deny automated HTTP access stay configured below
# as disabled sources instead of attempting to bypass their controls.
SOURCES: tuple[EditorialSource, ...] = (
    # Independent editorial coverage.
    EditorialSource(
        key="autosport_f1",
        provider="autosport.com",
        source_class="independent_editorial",
        mode="rss",
        discovery_url="https://www.autosport.com/rss/f1/news/",
    ),
    EditorialSource(
        key="motorsport_f1",
        provider="motorsport.com",
        source_class="independent_editorial",
        mode="rss",
        discovery_url="https://www.motorsport.com/rss/f1/news/",
    ),
    EditorialSource(
        key="the_race_f1",
        provider="the-race.com",
        source_class="independent_editorial",
        mode="listing",
        discovery_url="https://www.the-race.com/category/formula-1/",
        allowed_hosts=("www.the-race.com", "the-race.com"),
        article_path_pattern=r"^/formula-1/[^/]+/?$",
    ),
    EditorialSource(
        key="racefans_f1",
        provider="racefans.net",
        source_class="independent_editorial",
        mode="listing",
        discovery_url="https://www.racefans.net/category/formula-1/",
        allowed_hosts=("www.racefans.net", "racefans.net"),
        article_path_pattern=r"^/\d{4}/\d{2}/\d{2}/.+",
    ),
    EditorialSource(
        key="bbc_sport_f1",
        provider="bbc.com",
        source_class="independent_editorial",
        mode="listing",
        discovery_url="https://www.bbc.com/sport/formula1",
        allowed_hosts=("www.bbc.com", "bbc.com"),
        article_path_pattern=r"^/sport/formula1/articles/.+",
    ),
    EditorialSource(
        key="sky_sports_f1",
        provider="skysports.com",
        source_class="independent_editorial",
        mode="listing",
        discovery_url="https://www.skysports.com/f1/news",
        allowed_hosts=("www.skysports.com", "skysports.com"),
        article_path_pattern=r"^/f1/news/.+",
    ),
    # First-party team sources. Keep discovery paths narrow enough to avoid static
    # schedule/team/category pages and feeder-series content.
    EditorialSource(
        key="team_mclaren",
        provider="mclaren.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.mclaren.com/racing/formula-1/articles/",
        allowed_hosts=("www.mclaren.com", "mclaren.com"),
        article_path_pattern=(
            r"^/racing/formula-1/(?!articles/?$)(?!\d{4}/schedule/?$)"
            r"(?!drivers(?:/|$)|team(?:/|$)|car(?:/|$)).+"
        ),
        team_slug="mclaren",
    ),
    EditorialSource(
        key="team_mercedes",
        provider="mercedesamgf1.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.mercedesamgf1.com/news",
        allowed_hosts=("www.mercedesamgf1.com", "mercedesamgf1.com"),
        article_path_pattern=r"^/news/[^/]+/?$",
        team_slug="mercedes",
    ),
    EditorialSource(
        key="team_red_bull",
        provider="redbullracing.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.redbullracing.com/int-en",
        allowed_hosts=("www.redbullracing.com", "redbullracing.com"),
        article_path_pattern=(
            r"^/int-en/(?!drivers(?:/|$)|partners(?:/|$)|team(?:/|$)|cars(?:/|$)|"
            r"collections(?:/|$)|experiences(?:/|$)|events(?:/|$)).+"
        ),
        team_slug="red-bull-racing",
    ),
    EditorialSource(
        key="team_racing_bulls",
        provider="visacashapprb.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.visacashapprb.com/int-en/news",
        allowed_hosts=("www.visacashapprb.com", "visacashapprb.com"),
        article_path_pattern=(
            r"^/int-en/(?!news/?$|team(?:/|$)|drivers(?:/|$)|car(?:/|$)|"
            r"partners(?:/|$)|f1-academy(?:/|$)).+"
        ),
        team_slug="racing-bulls",
    ),
    EditorialSource(
        key="team_alpine",
        provider="alpinef1.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.alpinef1.com/news",
        allowed_hosts=("www.alpinef1.com", "alpinef1.com"),
        article_path_pattern=r"^/news/[a-z0-9][a-z0-9-]+/?$",
        team_slug="alpine",
    ),
    EditorialSource(
        key="team_haas",
        provider="haasf1team.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.haasf1team.com/news",
        allowed_hosts=("www.haasf1team.com", "haasf1team.com"),
        article_path_pattern=r"^/news/[^/]+/?$",
        team_slug="haas-f1-team",
    ),
    EditorialSource(
        key="team_audi",
        provider="audi.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.audi.com/en/audi-formula-racing-gmbh-17953",
        allowed_hosts=("www.audi.com", "audi.com"),
        article_path_pattern=r"^/en/press-releases/.+",
        team_slug="audi",
    ),
    EditorialSource(
        key="team_williams",
        provider="williamsf1.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.williamsf1.com/news",
        allowed_hosts=("www.williamsf1.com", "williamsf1.com"),
        article_path_pattern=(
            r"^/articles/[0-9a-f-]+/(?!.*(?:academy|formula-2|formula-3|f1-academy|f2-|f3-)).+"
        ),
        team_slug="williams",
    ),
    EditorialSource(
        key="team_aston_martin",
        provider="astonmartinf1.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.astonmartinf1.com/en-GB/news",
        allowed_hosts=("www.astonmartinf1.com", "astonmartinf1.com"),
        article_path_pattern=(
            r"^/en-GB/news/(?!announcement/?$|feature/?$|gallery/?$|heritage/?$|"
            r"esports/?$|on-track/?$)[^/]+/?$"
        ),
        team_slug="aston-martin",
    ),
    # Community signals are deliberately not treated as factual/editorial evidence.
    EditorialSource(
        key="reddit_formula1",
        provider="reddit:r/formula1",
        source_class="community_signal",
        mode="rss",
        discovery_url="https://www.reddit.com/r/formula1/.rss",
        rights_policy="metadata_summary_only",
    ),
    EditorialSource(
        key="reddit_f1technical",
        provider="reddit:r/F1Technical",
        source_class="community_signal",
        mode="rss",
        discovery_url="https://www.reddit.com/r/F1Technical/.rss",
        rights_policy="metadata_summary_only",
    ),
)

# These remain visible in the registry for provenance/planning, but are not fetched
# by default because live smoke testing receives explicit anti-bot/access denials.
DISABLED_SOURCES: tuple[EditorialSource, ...] = (
    EditorialSource(
        key="team_ferrari",
        provider="ferrari.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.ferrari.com/en-EN/formula1/news",
        allowed_hosts=("www.ferrari.com", "ferrari.com"),
        article_path_pattern=r"^/en-EN/formula1/articles/.+",
        team_slug="ferrari",
    ),
    EditorialSource(
        key="team_cadillac",
        provider="cadillacf1team.com",
        source_class="first_party_team",
        mode="listing",
        discovery_url="https://www.cadillacf1team.com/news",
        allowed_hosts=("www.cadillacf1team.com", "cadillacf1team.com"),
        article_path_pattern=r"^/news/.+",
        team_slug="cadillac",
    ),
)

DISABLED_SOURCE_REASONS = {
    "team_ferrari": "live server-side fetch is blocked by Ferrari anti-bot challenge (403)",
    "team_cadillac": "live server-side fetch is blocked by Cadillac F1 access controls (403)",
}

ALL_SOURCES = SOURCES + DISABLED_SOURCES
SOURCE_BY_KEY = {source.key: source for source in ALL_SOURCES}
