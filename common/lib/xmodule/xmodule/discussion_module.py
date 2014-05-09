# -*- coding: utf-8 -*-
from pkg_resources import resource_string

from xmodule.x_module import XModule
from xmodule.raw_module import RawDescriptor
from xmodule.editing_module import MetadataOnlyEditingDescriptor
from xblock.fields import String, Scope
from uuid import uuid4


class DiscussionFields(object):
    discussion_id = String(scope=Scope.settings, default="$$GUID$$")
    display_name = String(
        display_name="Nome Exibido",
        help="Nome de identificação deste módulo",
        default="Forum",
        scope=Scope.settings
    )
    data = String(
        help="XML data for the problem",
        scope=Scope.content,
        default="<discussion></discussion>"
    )
    discussion_category = String(
        display_name="Categoria",
        default="Semana 1",
        help="Um nome de categoria para este fórum. Este nome será exibido no painel esquerdo do fórum de discussão deste curso.",
        scope=Scope.settings
    )
    discussion_target = String(
        display_name="Subcategoria",
        default="Tópico a ser discutido",
        help="Um nome de subcategoria para este fórum. Este nome será exibido no painel esquerdo do fórum de discussão deste curso.",
        scope=Scope.settings
    )
    sort_key = String(scope=Scope.settings)


class DiscussionModule(DiscussionFields, XModule):
    js = {'coffee':
          [resource_string(__name__, 'js/src/time.coffee'),
          resource_string(__name__, 'js/src/discussion/display.coffee')]
          }
    js_module_name = "InlineDiscussion"

    def get_html(self):
        context = {
            'discussion_id': self.discussion_id,
        }
        return self.system.render_template('discussion/_discussion_module.html', context)


class DiscussionDescriptor(DiscussionFields, MetadataOnlyEditingDescriptor, RawDescriptor):

    def __init__(self, *args, **kwargs):
        super(DiscussionDescriptor, self).__init__(*args, **kwargs)
        # is this too late? i.e., will it get persisted and stay static w/ the first value
        # any code references. I believe so.
        if self.discussion_id == '$$GUID$$':
            self.discussion_id = uuid4().hex

    module_class = DiscussionModule
    # The discussion XML format uses `id` and `for` attributes,
    # but these would overload other module attributes, so we prefix them
    # for actual use in the code
    metadata_translations = dict(RawDescriptor.metadata_translations)
    metadata_translations['id'] = 'discussion_id'
    metadata_translations['for'] = 'discussion_target'

    @property
    def non_editable_metadata_fields(self):
        non_editable_fields = super(DiscussionDescriptor, self).non_editable_metadata_fields
        # We may choose to enable sort_keys in the future, but while Kevin is investigating....
        non_editable_fields.extend([DiscussionDescriptor.discussion_id, DiscussionDescriptor.sort_key])
        return non_editable_fields
