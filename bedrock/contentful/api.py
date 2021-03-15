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

def _get_product_class(product):
        product_themes = {
            'Firefox' : 'firefox',
            'Firefox Beta' : 'beta',
            'Firefox Developer' : 'developer',
            'Firefox Nightly' : 'nightly',
        }
        return 'mzp-t-product-' + product_themes[product] if product in product_themes else ''

def _get_abbr_from_width(width):
    widths = {
        'Extra Small' : 'xs',
        'Small' : 'sm',
        'Medium' : 'md',
        'Large' : 'lg',
        'Extra Large' : 'xl',
    }
    return widths[width] if width in widths else ''

def _get_width_class(width):
    width_abbr = _get_abbr_from_width(width)
    return 'mzp-t-content-' + width_abbr if width_abbr != '' else ''

def _get_theme_class(theme):
    return 'mzp-t-dark' if theme == "Dark" else ''


class ContentfulBase:
    def __init__(self):
        self.client = get_client()

class ContentfulPage(ContentfulBase):
    #TODO: List: stop list items from being wrapped in paragraph tags
    #TODO: List: add class to lists to format
    #TODO: If last item in content is a p:only(a) add cta link class?
    renderer = RichTextRenderer({
        'bold': StrongRenderer,
    })
    client = None

    def get_all_page_data(self):
        pages = self.client.entries({'content_type': 'pageVersatile'})
        return [self.get_page_data(p.id) for p in pages]

    def get_page_data(self, page_id):
        page = self.client.entry(page_id, {'include': 5})
        page_data = {
            'id': page.id,
            'content_type': page.content_type.id,
        }
        return page_data

    # page entry
    def get_entry_data(self, page_id):
        entry_data = self.client.entry(page_id)
        # print(entry_data.__dict__)
        return entry_data

    # any entry
    def get_entry_by_id(self, entry_id):
        return self.client.entry(entry_id)

    def get_info_data(self, page_id):
        page_obj = self.client.entry(page_id)
        fields = page_obj.fields()

        info_data = {
            'title': fields['preview_title'],
            'blurb': fields['preview_blurb'],
            'slug': fields['slug'],
        }

        if 'preview_image' in fields:
            preview_image_url = fields['preview_image'].fields().get('file').get('url')
            info_data['image'] = 'https:' + preview_image_url

        return info_data

    def get_content(self, page_id):
        page_obj = self.client.entry(page_id)
        page_type = page_obj.sys.get('content_type').id
        fields = page_obj.fields()

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
            #versatile
            content = fields.get('content')

            # get components from content
            for item in content:
                content_type = item.sys.get('content_type').id
                if content_type == 'componentHero':
                    entries.append(self.get_hero_data(item.id))
                elif content_type == 'layoutCallout':
                    entries.append(self.get_callout_data(item.id))
        elif page_type == 'pageHome':
            #home
            entries = []
        #TODO: error if not found

        return entries

    def get_text_data(self, value):
        text_data = {
            'component': 'text',
            'body': self.renderer.render(value),
            'width_class': _get_width_class('Medium') #TODO
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
            'cta': self.get_cta_data(fields.get('cta').id) if fields.get('cta') else {'include_cta': False,}
        }

        #print(hero_data)

        return hero_data

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
            'cta': self.get_cta_data(content_fields.get('cta').id) if content_fields.get('cta') else {'include_cta': False,}
        }

        return callout_data

    def get_cta_data(self, cta_id):
        cta_obj = self.get_entry_by_id(cta_id)
        cta_fields = cta_obj.fields()

        cta_data = {
            'component': cta_obj.sys.get('content_type').id,
            'label': cta_fields.get('label'),
            'action': cta_fields.get('action'),
            'size': 'mzp-t-xl',  #TODO
            'theme': 'mzp-t-primary',  #TODO
            'include_cta': True,
        }
        return cta_data


contentful_preview_page = ContentfulPage()


#TODO make optional fields optional
