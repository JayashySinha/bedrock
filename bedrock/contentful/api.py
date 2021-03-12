from django.conf import settings

import contentful as api
from rich_text_renderer import RichTextRenderer
from rich_text_renderer.text_renderers import BaseInlineRenderer


# Bedrock to Contentful locale map
LOCALE_MAP = {
    'de': 'de-DE',
}


class StrongRenderer(BaseInlineRenderer):
    @property
    def _render_tag(self):
        return 'strong'


renderer = RichTextRenderer({
    'bold': StrongRenderer,
})


def get_client():
    client = None
    if settings.CONTENTFUL_SPACE_ID:
        client = api.Client(
            settings.CONTENTFUL_SPACE_ID,
            settings.CONTENTFUL_SPACE_KEY,
            api_url=settings.CONTENTFUL_SPACE_API,
        )

    return client


def contentful_locale(locale):
    """Returns the Contentful locale for the Bedrock locale"""
    if locale.startswith('es-'):
        return 'es'

    return LOCALE_MAP.get(locale, locale)


def _get_height(width, aspect):
    height = 0
    if aspect == '1-1':
        height = width

    if aspect == '3-2':
        height = width * 0.6666

    if aspect == '16-9':
        height = width * 0.5625

    return round(height)


def _get_image_url(image, width, aspect):
    return 'https:' + image.url(
        w=width,
        h=_get_height(width, aspect),
        fit='fill',
        f='faces',
    )


class ContentfulBase:
    def __init__(self):
        self.client = get_client()
