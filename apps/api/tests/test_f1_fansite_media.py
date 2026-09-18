from app.ingestion.f1_fansite_media import (
    discover_gallery_urls,
    parse_gallery_html,
)


def test_f1_fansite_gallery_discovery_is_scoped_to_wallpaper_pages() -> None:
    html = """
    <a href="/f1-wallpaper/photos-of-the-2026-austrian-formula-1-grand-prix-race/">
      Austria
    </a>
    <a href="/news/example">News</a>
    <a href="https://example.com/f1-wallpaper/not-ours/">External</a>
    """

    assert discover_gallery_urls(
        html,
        base_url="https://www.f1-fansite.com/f1-wallpapers/",
    ) == [
        "https://www.f1-fansite.com/f1-wallpaper/"
        "photos-of-the-2026-austrian-formula-1-grand-prix-race/"
    ]


def test_f1_fansite_parser_keeps_origin_and_rights_metadata() -> None:
    html = """
    <article>
      <h1>Photos of Sunday 2026 Monaco Formula 1 Grand Prix</h1>
      <figure>
        <a href="/wp-content/uploads/2026/06/hadjar-monaco.jpg">
          <img
            src="/wp-content/uploads/2026/06/hadjar-monaco-small.jpg"
            alt="Isack Hadjar on the Monaco podium"
          />
        </a>
        <figcaption>
          MONTE-CARLO, MONACO - Isack Hadjar on the podium.
          (Photo by Anni Graf/LAT Images)
          // Getty Images / Red Bull Content Pool //
          SI202606070445 // Usage for editorial use only //
        </figcaption>
      </figure>
    </article>
    """

    item = parse_gallery_html(
        html,
        gallery_url=(
            "https://www.f1-fansite.com/f1-wallpaper/"
            "photos-of-sunday-2026-monaco-formula-1-grand-prix/"
        ),
    )[0]

    assert item.image_url.endswith("/hadjar-monaco.jpg")
    assert item.gallery_title == (
        "Photos of Sunday 2026 Monaco Formula 1 Grand Prix"
    )
    assert item.content_role == "podium"
    assert item.photographer == "Anni Graf"
    assert item.agency == "LAT Images"
    assert item.origin_provider == "red_bull_content_pool"
    assert item.origin_asset_id == "SI202606070445"
    assert item.rights_note == "editorial use only"



def test_f1_fansite_parser_rejects_page_thumbnails_and_affiliate_banners() -> None:
    html = """
    <article>
      <h1>Photos of Friday Practice before the 2026 Italian F1 GP</h1>
      <img src="/wp-content/uploads/2026/09/18-friday-monza-2026-330x220.jpg" alt="thumbnail" />
      <img src="/wp-content/uploads/2026/07/F1-Launch_Refresh2_Static_Affiliate_728x90_US-EN.jpg" alt="Try F1 on Apple TV" />
      <figure>
        <a href="/wp-content/uploads/2026/09/32-friday-monza-2026-990x660.jpg">
          <img src="/wp-content/uploads/2026/09/32-friday-monza-2026-330x220.jpg" alt="Lewis Hamilton on track" />
        </a>
        <figcaption>Lewis Hamilton on track at Monza</figcaption>
      </figure>
    </article>
    """

    items = parse_gallery_html(
        html,
        gallery_url=(
            "https://www.f1-fansite.com/f1-wallpaper/"
            "photos-of-friday-practice-before-the-2026-italian-f1-gp/"
        ),
    )

    assert len(items) == 1
    assert items[0].image_url.endswith("32-friday-monza-2026-990x660.jpg")
    assert items[0].caption == "Lewis Hamilton on track at Monza"


def test_f1_fansite_parser_rejects_small_figure_without_full_asset() -> None:
    html = """
    <article>
      <h1>2026 British F1 GP</h1>
      <figure>
        <img src="/wp-content/uploads/2026/07/20-thursday-silverstone-2026-330x220.jpg" alt="thumbnail only" />
      </figure>
    </article>
    """

    assert parse_gallery_html(
        html,
        gallery_url=(
            "https://www.f1-fansite.com/f1-wallpaper/"
            "photos-of-the-2026-british-f1-gp/"
        ),
    ) == []



def test_f1_fansite_parser_accepts_large_gallery_image_outside_figure() -> None:
    html = """
    <article>
      <h1>Photos of Friday Practice before the 2026 Italian F1 GP</h1>
      <img
        src="/wp-content/uploads/2026/09/32-friday-monza-2026-990x660.jpg"
        alt="Lewis Hamilton on track at Monza"
      />
    </article>
    """

    items = parse_gallery_html(
        html,
        gallery_url=(
            "https://www.f1-fansite.com/f1-wallpaper/"
            "photos-of-friday-practice-before-the-2026-italian-f1-gp/"
        ),
    )

    assert len(items) == 1
    assert items[0].image_url.endswith("32-friday-monza-2026-990x660.jpg")
