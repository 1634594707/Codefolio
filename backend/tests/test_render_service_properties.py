import importlib

_hypothesis = importlib.import_module("hypothesis")
given = _hypothesis.given
settings = _hypothesis.settings
st = importlib.import_module("hypothesis.strategies")

from models import CardData
from services.render_service import RenderService


@st.composite
def card_data_strategy(draw) -> CardData:
    username = draw(st.from_regex(r"[A-Za-z0-9-]{1,20}", fullmatch=True))
    return CardData(
        username=username,
        avatar_url=f"https://avatars.example.com/{username}.png",
        gitscore=draw(st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)),
        radar_chart_data=draw(st.lists(st.floats(min_value=0.0, max_value=33.0, allow_nan=False, allow_infinity=False), min_size=5, max_size=5)),
        style_tags=draw(st.lists(st.text(min_size=1, max_size=16), max_size=4)),
        roast_comment=draw(st.text(max_size=120)),
        tech_icons=draw(st.lists(st.text(min_size=1, max_size=12), max_size=4)),
    )


@settings(max_examples=200)
@given(
    card_data=card_data_strategy(),
    tech_summary=st.text(max_size=200),
    language=st.sampled_from(["en", "zh"]),
)
def test_social_card_theme_changes_rendered_html(card_data: CardData, tech_summary: str, language: str) -> None:
    service = RenderService()
    dark_html = service.generate_social_card_html(card_data, tech_summary=tech_summary, theme="dark", language=language)
    light_html = service.generate_social_card_html(card_data, tech_summary=tech_summary, theme="light", language=language)

    assert dark_html != light_html
    assert "#17181c" in dark_html
    assert "#efe8dc" in light_html
