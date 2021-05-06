from django.conf import settings

import contentful as api
from rich_text_renderer import RichTextRenderer
from rich_text_renderer.text_renderers import BaseInlineRenderer


# Bedrock to Contentful locale map
LOCALE_MAP = {
    'de': 'de-DE',
}
ASPECT_RATIOS = {
    '1:1': '1-1',
    '3:2': '3-2',
    '16:9': '16-9',
}
ASPECT_MULTIPLIER = {
    '1:1': 1,
    '3:2': 0.6666,
    '16:9': 0.5625
}
PRODUCT_THEMES = {
    'Firefox': 'firefox',
    'Firefox Beta': 'beta',
    'Firefox Developer': 'developer',
    'Firefox Nightly': 'nightly',
}
WIDTHS = {
    'Extra Small': 'xs',
    'Small': 'sm',
    'Medium': 'md',
    'Large': 'lg',
    'Extra Large': 'xl',
}
LAYOUT_CLASS = {
    'layout2Cards': 'mzp-l-card-half',
    'layout3Cards': 'mzp-l-card-third',
    'layout4Cards': 'mzp-l-card-quarter',
    'layout5Cards': 'mzp-l-card-hero',
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
            environment='V0',
            api_url=settings.CONTENTFUL_SPACE_API,
        )

    return client


def contentful_locale(locale):
    """Returns the Contentful locale for the Bedrock locale"""
    if locale.startswith('es-'):
        return 'es'

    return LOCALE_MAP.get(locale, locale)


def _get_height(width, aspect):
    return round(width * ASPECT_MULTIPLIER.get(aspect, 0))


def _get_image_url(image, width, aspect):
    return 'https:' + image.url(
        w=width,
        h=_get_height(width, aspect),
        fit='fill',
        f='faces',
    )


def _get_product_class(product):
    return f'mzp-t-product-{PRODUCT_THEMES.get(product, "")}'


def _get_layout_class(layout):
    return LAYOUT_CLASS.get(layout, '')


def _get_abbr_from_width(width):
    return WIDTHS.get(width, '')


def _get_aspect_ratio_class(aspect_ratio):
    return f'mzp-has-aspect-{ASPECT_RATIOS.get(aspect_ratio, "")}'


def _get_width_class(width):
    width_abbr = _get_abbr_from_width(width)
    return f'mzp-t-content-{width_abbr}'


def _get_theme_class(theme):
    return 'mzp-t-dark' if theme == "Dark" else ''


class ContentfulBase:
    def __init__(self):
        self.client = get_client()


class ContentfulPage(ContentfulBase):
    # TODO: List: stop list items from being wrapped in paragraph tags
    # TODO: List: add class to lists to format
    # TODO: If last item in content is a p:only(a) add cta link class?
    renderer = RichTextRenderer({
        'bold': StrongRenderer,
    })
    client = None

    def get_all_page_data(self):
        pages = self.client.entries({'content_type': 'pageVersatile'})
        return [self.get_page_data(p.id) for p in pages]

    def get_page_data(self, page_id):
        page = self.client.entry(page_id, {'include': 5})
        fields = page.fields()
        page_data = {
            'page_type': page.content_type.id,
            'info': self.get_info_data(fields),
            'fields': fields,
        }
        return page_data

    # page entry
    def get_entry_data(self, page_id):
        entry_data = self.client.entry(page_id)
        # print(entry_data.__dict__)
        return entry_data

    def get_page_type(self, page_id):
        page_obj = self.client.entry(page_id)
        page_type = page_obj.sys.get('content_type').id
        return page_type

    # any entry
    def get_entry_by_id(self, entry_id):
        return self.client.entry(entry_id)

    @staticmethod
    def get_info_data(fields):
        info_data = {
            'title': fields['preview_title'],
            'blurb': fields['preview_blurb'],
            'slug': fields.get('slug', 'home'),
        }

        if 'preview_image' in fields:
            preview_image_url = fields['preview_image'].fields().get('file').get('url')
            info_data['image'] = 'https:' + preview_image_url

        return info_data

    def get_content(self, page_id):
        page_data = self.get_page_data(page_id)
        page_type = page_id['page_type']
        fields = page_data['fields']

        entries = []
        if page_type == 'pageGeneral':
            # general
            # look through all entries and find content ones
            for key, value in fields.items():
                if key == 'component_hero':
                    entries.append(self.get_hero_data(value.id))
                elif key == 'body':
                    entries.append(self.get_text_data(value))
                elif key == 'layout_callout':
                    entries.append(self.get_callout_data(value.id))
        elif page_type == 'pageVersatile':
            # versatile
            content = fields.get('content')

            # get components from content
            for item in content:
                content_type = item.sys.get('content_type').id
                if content_type == 'componentHero':
                    entries.append(self.get_hero_data(item.id))
                elif content_type == 'layoutCallout':
                    entries.append(self.get_callout_data(item.id))
        elif page_type == 'pageHome':
            # home
            content = fields.get('content')

            # get components from content
            for item in content:
                content_type = item.sys.get('content_type').id
                if content_type == 'componentHero':
                    entries.append(self.get_hero_data(item.id))
                elif content_type == 'componentSectionHeading':
                    entries.append(self.get_section_heading_data(item.id))
                elif content_type == 'layoutCallout':
                    entries.append(self.get_callout_data(item.id))
                elif content_type == 'layout2Cards':
                    entries.append(self.get_card_layout_data(item.id))
                elif content_type == 'layout3Cards':
                    entries.append(self.get_card_layout_data(item.id))
                elif content_type == 'layout5Cards':
                    entries.append(self.get_card_layout_data(item.id))
        # TODO: error if not found

        return {
            'page_type': page_type,
            'info': page_data['info'],
            'entries': entries,
        }

    def get_text_data(self, value):
        text_data = {
            'component': 'text',
            'body': self.renderer.render(value),
            'width_class': _get_width_class('Medium')  # TODO
        }

        return text_data

    def get_hero_data(self, hero_id):
        hero_obj = self.get_entry_by_id(hero_id)
        fields = hero_obj.fields()

        hero_image_url = fields['image'].fields().get('file').get('url')
        hero_reverse = fields.get('image_position')
        hero_body = self.renderer.render(fields.get('body'))

        hero_data = {
            'component': 'hero',
            'theme_class': _get_theme_class(fields.get('theme')),
            'product_class': _get_product_class(fields.get('product_icon')),
            'title': fields.get('heading'),
            'tagline': fields.get('tagline'),
            'body': hero_body,
            'image': 'https:' + hero_image_url,
            'image_position': fields.get('image_position'),
            'image_class': 'mzp-l-reverse' if hero_reverse == 'Left' else '',
            'cta': self.get_cta_data(fields.get('cta')),
        }

        return hero_data

    def get_section_heading_data(self, heading_id):
        heading_obj = self.get_entry_by_id(heading_id)
        fields = heading_obj.fields()

        heading_data = {
            'component': 'sectionHeading',
            'heading': fields.get('heading'),
        }

        return heading_data

    def get_callout_data(self, callout_id):
        config_obj = self.get_entry_by_id(callout_id)
        config_fields = config_obj.fields()

        content_id = config_fields.get('component_callout').id
        content_obj = self.get_entry_by_id(content_id)
        content_fields = content_obj.fields()
        content_body = self.renderer.render(content_fields.get('body')) if content_fields.get('body') else ''

        callout_data = {
            'component': 'callout',
            'theme_class': _get_theme_class(config_fields.get('theme')),
            'product_class': _get_product_class(content_fields.get('product_icon')),
            'title': content_fields.get('heading'),
            'body': content_body,
            'cta': self.get_cta_data(content_fields.get('cta')),
        }

        return callout_data

    def get_card_data(self, card_id, aspect_ratio):
        card_obj = self.get_entry_by_id(card_id)
        card_fields = card_obj.fields()
        card_body = self.renderer.render(card_fields.get('body')) if card_fields.get('body') else ''

        card_image = card_fields.get('image')
        highres_image_url = _get_image_url(card_image, 800, aspect_ratio)
        image_url = _get_image_url(card_image, 800, aspect_ratio)

        card_data = {
                'component': 'card',
                'heading': card_fields.get('heading'),
                'tag': card_fields.get('tag'),
                'link': card_fields.get('link'),
                'body': card_body,
                'aspect_ratio': _get_aspect_ratio_class(aspect_ratio),
                'highres_image_url': highres_image_url,
                'image_url': image_url,
            }

        return card_data

    def get_large_card_data(self, card_layout_id, card_id):
        large_card_layout = self.get_entry_by_id(card_layout_id)
        large_card_fields = large_card_layout.fields()

        # large card data
        large_card_image = large_card_fields.get('image')
        highres_image_url = _get_image_url(large_card_image, 1860, "16:9")
        image_url = _get_image_url(large_card_image, 1860, "16:9")

        # get card data
        card_data = self.get_card_data(card_id, "16:9")

        # over-write with large values
        card_data['component'] = 'large_card'
        card_data['highres_image_url'] = highres_image_url
        card_data['image_url'] = image_url

        large_card_data = card_data

        return large_card_data

    def get_card_layout_data(self, layout_id):
        config_obj = self.get_entry_by_id(layout_id)
        config_fields = config_obj.fields()
        aspect_ratio = config_fields.get('aspect_ratio')
        layout = config_obj.sys.get('content_type').id

        card_layout_data = {
            'component': 'cardLayout',
            'layout_class': _get_layout_class(layout),
            'aspect_ratio': aspect_ratio,
            'cards': [],
        }

        if layout == 'layout5Cards':
            card_layout_id = config_fields.get('large_card').id
            card_id = config_fields.get('large_card').fields().get('card').id
            large_card_data = self.get_large_card_data(card_layout_id, card_id)

            card_layout_data.get('cards').append(large_card_data)
            # TODO: first card after large card needs to be 1:1

        cards = config_fields.get('content')
        for card in cards:
            card_id = card.id
            card_data = self.get_card_data(card_id, aspect_ratio)
            card_layout_data.get('cards').append(card_data)

        return card_layout_data

    def get_cta_data(self, cta):
        if cta:
            cta_id = cta.id
        else:
            return {'include_cta': False}

        cta_obj = self.get_entry_by_id(cta_id)
        cta_fields = cta_obj.fields()

        cta_data = {
            'component': cta_obj.sys.get('content_type').id,
            'label': cta_fields.get('label'),
            'action': cta_fields.get('action'),
            'size': 'mzp-t-xl',  # TODO
            'theme': 'mzp-t-primary',  # TODO
            'include_cta': True,
        }
        return cta_data


contentful_preview_page = ContentfulPage()


# TODO make optional fields optional
