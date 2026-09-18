from app.ingestion.official_media_sources import (
    OFFICIAL_MEDIA_SOURCE_BY_KEY,
    access_block_reason,
    discover_source_pages,
    parse_official_media_page,
)


def test_formula1_media_discovery_stays_on_latest_articles() -> None:
    source = OFFICIAL_MEDIA_SOURCE_BY_KEY["formula1"]
    html = """
    <a href="/en/latest/article/gallery-best-images.abc123">Gallery</a>
    <a href="/en/racing/2026">Schedule</a>
    <a href="https://example.com/en/latest/article/not-ours.abc">External</a>
    """

    assert discover_source_pages(html, source=source) == [
        "https://www.formula1.com/en/latest/article/gallery-best-images.abc123"
    ]


def test_williams_media_discovery_uses_photo_article_pages() -> None:
    source = OFFICIAL_MEDIA_SOURCE_BY_KEY["williams"]
    html = """
    <a href="/articles/af07443f-67c4-4f28-9a42-5f6caf99c258/in-photos-our-weekend-in-monza">
      Monza gallery
    </a>
    <a href="/news">News index</a>
    """

    assert discover_source_pages(html, source=source) == [
        "https://www.williamsf1.com/articles/"
        "af07443f-67c4-4f28-9a42-5f6caf99c258/in-photos-our-weekend-in-monza"
    ]


def test_alpine_media_discovery_preserves_english_language() -> None:
    source = OFFICIAL_MEDIA_SOURCE_BY_KEY["alpine"]
    html = """
    <a href="/2026-formula-one-italian-grand-prix-friday/?lang=eng">
      Italian Grand Prix Friday
    </a>
    <a href="/brand-news/?lang=eng">Brand news</a>
    """

    assert discover_source_pages(html, source=source) == [
        "https://media.alpinecars.com/"
        "2026-formula-one-italian-grand-prix-friday?lang=eng"
    ]


def test_official_media_parser_selects_largest_srcset_and_filters_chrome() -> None:
    html = """
    <html>
      <head>
        <meta property="og:title" content="2026 Italian Grand Prix gallery" />
      </head>
      <body>
        <img src="/assets/team-logo.png" alt="Team logo" />
        <img
          src="/images/hamilton-400x225.jpg"
          srcset="
            /images/hamilton-400x225.jpg 400w,
            /images/hamilton-1200x675.jpg 1200w,
            /images/hamilton-2000x1125.jpg 2000w
          "
          alt="Lewis Hamilton driving on track at Monza"
        />
      </body>
    </html>
    """

    items = parse_official_media_page(
        html,
        page_url="https://example.com/gallery",
    )

    assert len(items) == 1
    assert items[0].image_url.endswith("hamilton-2000x1125.jpg")
    assert items[0].content_role == "driver_action"


def test_official_media_parser_keeps_figure_caption_and_credit() -> None:
    html = """
    <article>
      <h1>2026 Monaco Grand Prix</h1>
      <figure>
        <a href="/images/gasly-monaco-2400x1600.jpg">
          <img
            src="/images/gasly-monaco-800x533.jpg"
            alt="Pierre Gasly on the podium"
          />
        </a>
        <figcaption>
          Pierre Gasly celebrates on the podium. Photo by Alex Smith / Getty Images
        </figcaption>
      </figure>
    </article>
    """

    item = parse_official_media_page(
        html,
        page_url="https://example.com/monaco",
    )[0]

    assert item.image_url.endswith("gasly-monaco-2400x1600.jpg")
    assert item.content_role == "podium"
    assert item.photographer == "Alex Smith"
    assert item.origin_provider == "getty_images"


def test_media_source_access_challenge_is_detected() -> None:
    assert access_block_reason(
        "<html>Verify you are human</html>",
        response_url="https://example.com/page",
    ) == "anti_bot_challenge"
    assert access_block_reason(
        "<html>Register</html>",
        response_url="https://www.f1-fansite.com/register/",
    ) == "login_or_registration_redirect"



def test_williams_parser_unwraps_next_image_and_rejects_shop_assets() -> None:
    source = OFFICIAL_MEDIA_SOURCE_BY_KEY["williams"]
    html = """
    <html>
      <head>
        <meta property="article:published_time" content="2026-09-07T12:00:00Z" />
      </head>
      <body>
        <article>
          <h1>In Photos: Our weekend in Monza</h1>
          <img
            src="/_next/image?url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2Ffnx611yr%2Fproductionv2%2Fmonza-8192x5464.jpg%3Fw%3D1920%26h%3D1080%26auto%3Dformat&w=3840&q=75"
            alt="In Photos: Our weekend in Monza"
          />
          <img
            src="/_next/image?url=https%3A%2F%2Fmcprod.williamsf1.com%2Fmedia%2Fcatalog%2Fproduct%2Fcache%2Fx%2Fmiami_cover.jpg&w=3840&q=75"
            alt="AWF1 Team x Marvel - Iron Man: Racing Towards Doom Miami Special Edition Cover"
          />
        </article>
      </body>
    </html>
    """

    items = parse_official_media_page(
        html,
        page_url="https://www.williamsf1.com/articles/id/in-photos-our-weekend-in-monza",
        source=source,
    )

    assert len(items) == 1
    assert items[0].image_url.startswith("https://cdn.sanity.io/")
    assert "/_next/image" not in items[0].image_url
    assert items[0].season == 2026


def test_alpine_parser_filters_cross_event_cards_and_deduplicates_variants() -> None:
    source = OFFICIAL_MEDIA_SOURCE_BY_KEY["alpine"]
    html = """
    <html>
      <head>
        <meta property="article:published_time" content="2026-09-11T12:00:00Z" />
      </head>
      <body>
        <article>
          <h1>2026 Formula One Spanish Grand Prix, Friday</h1>
          <img
            src="/wp-content/uploads/2026/09/abcabcabcabcabcabcabcabcabcabcab-t.jpg"
            alt="Image - 2026 Formula One Spanish Grand Prix, Friday"
          />
          <img
            src="/wp-content/uploads/2026/09/abcabcabcabcabcabcabcabcabcabcab-m.jpg.webp"
            alt="Image - 2026 Formula One Spanish Grand Prix, Friday"
          />
          <img
            src="/wp-content/uploads/2026/09/abcabcabcabcabcabcabcabcabcabcab-l.jpg.webp"
            alt="Image - 2026 Formula One Spanish Grand Prix, Friday"
          />
          <img
            src="/wp-content/uploads/2026/09/defdefdefdefdefdefdefdefdefdefde-l.jpg.webp"
            alt="Image - 2026 Formula One Italian Grand Prix, Sunday"
          />
          <img
            src="/wp-content/uploads/2026/09/99999999999999999999999999999999-l.jpg.webp"
            alt="Image - BWT Alpine Formula One Team and SEALSQ announce a partnership"
          />
        </article>
      </body>
    </html>
    """

    items = parse_official_media_page(
        html,
        page_url=(
            "https://media.alpinecars.com/"
            "2026-formula-one-spanish-grand-prix-friday/?lang=eng"
        ),
        source=source,
    )

    assert len(items) == 1
    assert items[0].image_url.endswith(
        "abcabcabcabcabcabcabcabcabcabcab-l.jpg.webp"
    )
    assert items[0].season == 2026


def test_parser_prefers_article_scope_over_related_page_images() -> None:
    html = """
    <html>
      <body>
        <main>
          <article>
            <h1>2026 Italian Grand Prix gallery</h1>
            <img
              src="/images/monza-2000x1200.jpg"
              alt="Cars driving on track at Monza"
            />
          </article>
          <section>
            <img
              src="/images/related-2000x1200.jpg"
              alt="Unrelated promotional feature"
            />
          </section>
        </main>
      </body>
    </html>
    """

    items = parse_official_media_page(
        html,
        page_url="https://example.com/gallery",
    )

    assert len(items) == 1
    assert items[0].image_url.endswith("monza-2000x1200.jpg")
