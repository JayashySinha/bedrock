from django.conf import settings
from urllib.parse import urlparse, parse_qs

import contentful as api
from crum import get_current_request
from rich_text_renderer import RichTextRenderer
from rich_text_renderer.base_node_renderer import BaseNodeRenderer
from rich_text_renderer.block_renderers import BaseBlockRenderer
from rich_text_renderer.text_renderers import BaseInlineRenderer

from lib.l10n_utils import render_to_string


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
    'Firefox': 'family',
    'Firefox Browser': 'firefox',
    'Firefox Browser Beta': 'beta',
    'Firefox Browser Developer': 'developer',
    'Firefox Browser Nightly': 'nightly',
    'Firefox Browser Focus': 'focus',
    'Firefox Monitor': 'monitor',
    'Firefox Lockwise': 'lockwise',
    'Mozilla': 'mozilla',
    'Mozilla VPN': 'vpn',
    'Pocket': 'pocket',
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
THEME_CLASS = {
    'Light': '',
    'Light (alternative)': 'mzp-t-background-alt',
    'Dark': 'mzp-t-dark',
    'Dark (alternative)': 'mzp-t-dark mzp-t-background-alt',
}
COLUMN_CLASS = {
    '1': '',
    '2': 'mzp-l-columns mzp-t-columns-two ',
    '3': 'mzp-l-columns mzp-t-columns-three',
    '4': 'mzp-l-columns mzp-t-columns-four',
}


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


def _get_image_url(image, width):
    return 'https:' + image.url(
        w=width,
    )

def _get_card_image_url(image, width, aspect):
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
    return f'mzp-t-content-{WIDTHS.get(width, "")}'


def _get_theme_class(theme):
    return THEME_CLASS.get(theme, '')


def _get_youtube_id(youtube_url):
    url_data = urlparse(youtube_url)
    queries = parse_qs(url_data.query)
    youtube_id = queries["v"][0]
    return youtube_id


def _get_column_class(columns):
    return COLUMN_CLASS.get(columns, '')


def _make_logo(entry):
    product = entry.fields()['product']

    data = {
        'logo_size': 'md', # TODO
        'product_name': product,
        'product_icon': PRODUCT_THEMES.get(product, ""),
    }

    return render_to_string('logo.html', data, get_current_request())


def _make_wordmark(entry):
    product = entry.fields()['product']

    data = {
        'logo_size': 'md', # TODO
        'product_name': product,
        'product_icon': PRODUCT_THEMES.get(product, ""),
    }

    return render_to_string('wordmark.html', data, get_current_request())


def _make_cta_button(entry):
#     # print(entry.fields())

# def get_cta_data(self, cta):
#         if cta:
#             cta_id = cta.id
#         else:
#             return {'include_cta': False}

#         cta_obj = self.get_entry_by_id(cta_id)
#         cta_fields = cta_obj.fields()

#         cta_data = {
#             'component': cta_obj.sys.get('content_type').id,
#             'label': cta_fields.get('label'),
#             'action': cta_fields.get('action'),
#             'size': 'mzp-t-xl',  # TODO
#             'theme': 'mzp-t-primary',  # TODO
#             'include_cta': True,
#         }
#         return cta_data

    fields = entry.fields()

    button_class = [
        'mzp-t-product', # TODO, not product on Mozilla pages
        'mzp-t-secondary' if fields.get('theme') == 'Secondary' else '',
    ]

    data = {
        'action': fields.get('action'),
        'label': fields.get('label'),
        'button_size': WIDTHS.get(fields.get("size"), ""),
        'button_class': ' '.join(button_class),

    }
    return render_to_string('cta.html', data, get_current_request())


class StrongRenderer(BaseInlineRenderer):
    @property
    def _render_tag(self):
        return 'strong'


def _render_list(tag, content):
    return f"<{tag} class='mzp-u-list-styled'>{content}</{tag}>"


class UlRenderer(BaseBlockRenderer):
    def render(self, node):
        return _render_list('ul', self._render_content(node))


class OlRenderer(BaseBlockRenderer):
    def render(self, node):
        return _render_list('ol', self._render_content(node))


class InlineEntryRenderer(BaseNodeRenderer):
    def render(self, node):
        entry = node['data']['target']
        content_type = entry.sys.get('content_type').id

        if content_type == 'componentLogo':
            return _make_logo(entry)
        elif content_type == 'componentWordmark':
            return _make_wordmark(entry)
        elif content_type == 'componentCtaButton':
            return _make_cta_button(entry)
        else:
            return content_type


class ContentfulBase:
    client = None

    def __init__(self):
        self.client = get_client()


class ContentfulPage(ContentfulBase):
    # TODO: List: stop list items from being wrapped in paragraph tags
    # TODO: Don't output empty paragraph tags
    # TODO: If last item in content is a p:only(a) add cta link class?
    # TODO: Error/ Warn / Transform links to allizom
    _renderer = RichTextRenderer({
        'bold': StrongRenderer,
        'Unordered-list': UlRenderer,
        'ordered-list': OlRenderer,
        'embedded-entry-inline': InlineEntryRenderer,
    })

    def render_rich_text(self, node):
        self._renderer.render(node)

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
        page_type = page_data['page_type']
        fields = page_data['fields']
        content = None

        entries = []
        if page_type == 'pageGeneral':
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
        elif page_type == 'pageHome':
            # home
            content = fields.get('content')

        if content:
            # get components from content
            for item in content:
                content_type = item.sys.get('content_type').id
                if content_type == 'componentHero':
                    entries.append(self.get_hero_data(item.id))
                elif content_type == 'componentSectionHeading':
                    entries.append(self.get_section_heading_data(item.id))
                elif content_type == 'componentSplitBlock':
                    entries.append(self.get_split_data(item.id))
                elif content_type == 'layoutCallout':
                    entries.append(self.get_callout_data(item.id))
                elif content_type == 'layout2Cards':
                    entries.append(self.get_card_layout_data(item.id))
                elif content_type == 'layout3Cards':
                    entries.append(self.get_card_layout_data(item.id))
                elif content_type == 'layout4Cards':
                    entries.append(self.get_card_layout_data(item.id))
                elif content_type == 'layout5Cards':
                    entries.append(self.get_card_layout_data(item.id))
                elif content_type == 'layoutPictoBlocks':
                    entries.append(self.get_picto_layout_data(item.id))
                elif content_type == 'textOneColumn':
                    entries.append(self.get_text_column_data(1, item.id))
                elif content_type == 'textTwoColumns':
                    entries.append(self.get_text_column_data(2, item.id))
                elif content_type == 'textThreeColumns':
                    entries.append(self.get_text_column_data(3, item.id))

        return {
            'page_type': page_type,
            'info': page_data['info'],
            'entries': entries,
        }

    def get_text_data(self, value):
        text_data = {
            'component': 'text',
            'body': self.render_rich_text(value),
            'width_class': _get_width_class('Medium')  # TODO
        }

        return text_data

    def get_hero_data(self, hero_id):
        hero_obj = self.get_entry_by_id(hero_id)
        fields = hero_obj.fields()

        hero_image_url = fields['image'].fields().get('file').get('url')
        hero_reverse = fields.get('image_side')
        hero_body = self.render_rich_text(fields.get('body'))

        hero_data = {
            'component': 'hero',
            'theme_class': _get_theme_class(fields.get('theme')),
            'product_class': _get_product_class(fields.get('product_icon')),
            'title': fields.get('heading'),
            'tagline': fields.get('tagline'),
            'body': hero_body,
            'image': 'https:' + hero_image_url,
            'image_class': 'mzp-l-reverse' if hero_reverse == 'Left' else '',
            'include_cta': True if fields.get('cta') else False,
            'cta': _make_cta_button(fields.get('cta')),
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

    def get_split_data(self, split_id):

        SPLIT_LAYOUT_CLASS = {
            'Even': '',
            'Narrow': 'mzp-l-split-body-narrow',
            'Wide': 'mzp-l-split-body-wide',
        }

        SPLIT_MEDIA_WIDTH_CLASS = {
            'Fill available width': '',
            'Fill available height': 'mzp-l-split-media-constrain-height',
            'Overflow container': 'mzp-l-split-media-overflow',
        }

        SPLIT_V_ALIGN_CLASS = {
            'Top': 'mzp-l-split-v-start',
            'Center': 'mzp-l-split-v-center',
            'Bottom': 'mzp-l-split-v-end',
        }

        SPLIT_H_ALIGN_CLASS = {
            'Left': 'mzp-l-split-h-start',
            'Center': 'mzp-l-split-h-center',
            'Right': 'mzp-l-split-h-end',
        }

        SPLIT_POP_CLASS = {
            'None': '',
            'Both': 'mzp-l-split-pop',
            'Top': 'mzp-l-split-pop-top',
            'Bottom': 'mzp-l-split-pop-bottom',
        }

        split_obj = self.get_entry_by_id(split_id)
        fields = split_obj.fields()

        def get_block_class():

            block_classes = [
                'mzp-l-split-reversed' if fields.get('image_side') == 'Left' else '',
                SPLIT_LAYOUT_CLASS.get(fields.get('body_width'), ''),
                SPLIT_POP_CLASS.get(fields.get('image_pop'), ''),
            ]

            return ' '.join(block_classes)

        def get_body_class():
            body_classes = [
                SPLIT_V_ALIGN_CLASS.get(fields.get('body_vertical_alignment'), ''),
                SPLIT_H_ALIGN_CLASS.get(fields.get('body_horizontal_alignment'), '')
            ]
            return ' '.join(body_classes)

        def get_media_class():
            media_classes = [
                SPLIT_MEDIA_WIDTH_CLASS.get(fields.get('image_width'), '')
            ]
            # v_align_class = SPLIT_V_ALIGN_CLASS.get(fields.get('image_vertical_alignment'), '')
            # h_align_class = SPLIT_H_ALIGN_CLASS.get(fields.get('image_horizontal_alignment'), '')

            return ' '.join(media_classes)

        def get_mobile_class():
            mobile_classes = [
                'mzp-l-split-center-on-sm-md' if 'Center content' in fields.get('mobile_display') else '',
                'mzp-l-split-hide-media-on-sm-md' if 'Hide image' in fields.get('mobile_display') else '',
            ]

            return ' '.join(mobile_classes)


        split_image_url = fields['image'].fields().get('file').get('url')

        split_data = {
            'component': 'split',
            'block_class': get_block_class(),
            'theme_class': _get_theme_class(fields.get('theme')),
            'has_bg': True if _get_theme_class(fields.get('theme')) != '' else False,
            'body_class': get_body_class(),
            'body': self.render_rich_text(fields.get('body')),
            'media_class': get_media_class(),
            'image': 'https:' + split_image_url, #TODO max width
            'mobile_class': get_mobile_class(),
        }

        #print(self.render(fields.get('body')))

        return split_data

    def get_callout_data(self, callout_id):
        config_obj = self.get_entry_by_id(callout_id)
        config_fields = config_obj.fields()

        content_id = config_fields.get('component_callout').id
        content_obj = self.get_entry_by_id(content_id)
        content_fields = content_obj.fields()
        content_body = self.render_rich_text(content_fields.get('body')) if content_fields.get('body') else ''

        callout_data = {
            'component': 'callout',
            'theme_class': _get_theme_class(config_fields.get('theme')),
            'product_class': _get_product_class(content_fields.get('product_icon')),
            'title': content_fields.get('heading'),
            'body': content_body,
            'cta': _make_cta_button(content_fields.get('cta')),
        }

        return callout_data

    def get_card_data(self, card_id, aspect_ratio):
        # need a fallback aspect ratio
        aspect_ratio = aspect_ratio or '16:9'
        card_obj = self.get_entry_by_id(card_id)
        card_fields = card_obj.fields()
        card_body = self.render_rich_text(card_fields.get('body')) if card_fields.get('body') else ''

        if 'image' in card_fields:
            card_image = card_fields.get('image')
            # TODO smaller image files when layout allows it
            highres_image_url = _get_card_image_url(card_image, 800, aspect_ratio)
            image_url = _get_card_image_url(card_image, 800, aspect_ratio)
        else:
            image_url = ''

        if 'you_tube' in card_fields:
            youtube_id = _get_youtube_id(card_fields.get('you_tube'))
        else:
            youtube_id = ''

        card_data = {
                'component': 'card',
                'heading': card_fields.get('heading'),
                'tag': card_fields.get('tag'),
                'link': card_fields.get('link'),
                'body': card_body,
                'aspect_ratio': _get_aspect_ratio_class(aspect_ratio) if image_url != '' else '',
                'highres_image_url': highres_image_url,
                'image_url': image_url,
                'youtube_id': youtube_id,
            }

        return card_data

    def get_large_card_data(self, card_layout_id, card_id):
        large_card_layout = self.get_entry_by_id(card_layout_id)
        large_card_fields = large_card_layout.fields()

        # large card data
        large_card_image = large_card_fields.get('image')
        highres_image_url = _get_card_image_url(large_card_image, 1860, "16:9")
        image_url = _get_card_image_url(large_card_image, 1860, "16:9")

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

        follows_large_card = False
        if layout == 'layout5Cards':
            card_layout_id = config_fields.get('large_card').id
            card_id = config_fields.get('large_card').fields().get('card').id
            large_card_data = self.get_large_card_data(card_layout_id, card_id)

            card_layout_data.get('cards').append(large_card_data)
            follows_large_card = True

        cards = config_fields.get('content')
        for card in cards:
            if follows_large_card == True:
                this_aspect = '1:1'
                follows_large_card = False
            else:
                this_aspect = aspect_ratio
            card_id = card.id
            card_data = self.get_card_data(card_id, this_aspect)
            card_layout_data.get('cards').append(card_data)

        return card_layout_data


    def get_picto_data(self, picto_id):
        picto_obj = self.get_entry_by_id(picto_id)
        picto_fields = picto_obj.fields()
        picto_body = self.render_rich_text(picto_fields.get('body')) if picto_fields.get('body') else ''

        if 'icon' in picto_fields:
            picto_image = picto_fields.get('icon')
            image_url = _get_image_url(picto_image, 800)
        else:
            image_url = '' # TODO: this should cause an error, the macro requires an image

        picto_data = {
                'component': 'picto',
                'heading': picto_fields.get('heading'),
                'body': picto_body,
                'image_url': image_url,
            }

        return picto_data

    def get_picto_layout_data(self, layout_id):

        def get_layout_class():
            layout_classes = [
                _get_width_class(config_fields.get('width')) if config_fields.get('width') else '',
                _get_column_class(str(config_fields.get('blocks_per_row')) if config_fields.get('blocks_per_row') else '3'),
                'mzp-t-picto-side' if config_fields.get('icon_position') == 'Side' else '',
                'mzp-t-picto-center' if config_fields.get('block_alignment') == 'Center' else '',
                _get_theme_class(config_fields.get('theme')) if config_fields.get('theme') else '',
            ]

            return ' '.join(layout_classes)

        config_obj = self.get_entry_by_id(layout_id)
        config_fields = config_obj.fields()
        layout = config_obj.sys.get('content_type').id

        picto_layout_data = {
            'component': 'pictoLayout',
            'layout_class': get_layout_class(),
            'heading_level': config_fields.get('heading_level')[1:] if config_fields.get('heading_level') else 3,
            'image_width': 64,
            'pictos': [],
        }

        pictos = config_fields.get('content')
        for picto in pictos:
            picto_id = picto.id
            picto_data = self.get_picto_data(picto_id)
            picto_layout_data.get('pictos').append(picto_data)

        return picto_layout_data

    def get_text_column_data(self, cols, text_id):
        entry_obj = self.get_entry_by_id(text_id)
        fields = entry_obj.fields()

        def get_content_class():
            content_classes = [
                _get_width_class(fields.get('width')) if fields.get('width') else '',
                _get_column_class(str(cols)),
                _get_theme_class(fields.get('theme')) if fields.get('theme') else '',
            ]

            return ' '.join(content_classes)

        text_data = {
            'component': 'textColumns',
            'layout_class': get_content_class(),
            'content': [self.render_rich_text(fields.get('body_column_one')) if fields.get('body_column_one') else ''],
        }

        if cols > 1:
            text_data['content'].append(self.render_rich_text(fields.get('body_column_two')) if fields.get('body_column_two') else '')
        if cols > 2:
            text_data['content'].append(self.render_rich_text(fields.get('body_column_three')) if fields.get('body_column_three') else '')

        return text_data

contentful_preview_page = ContentfulPage()


# TODO make optional fields optional
