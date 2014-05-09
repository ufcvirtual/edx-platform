# -*- coding: utf-8 -*-
# pylint: disable=W0223
"""Video is ungraded Xmodule for support video content.
It's new improved video module, which support additional feature:

- Can play non-YouTube video sources via in-browser HTML5 video player.
- YouTube defaults to HTML5 mode from the start.
- Speed changes in both YouTube and non-YouTube videos happen via
in-browser HTML5 video method (when in HTML5 mode).
- Navigational subtitles can be disabled altogether via an attribute
in XML.
"""

import json
import logging

from lxml import etree
from pkg_resources import resource_string
import datetime
import time
import copy

from django.http import Http404
from django.conf import settings
from django.utils.translation import ugettext as _

from xmodule.x_module import XModule
from xmodule.editing_module import TabsEditingDescriptor
from xmodule.raw_module import EmptyDataRawDescriptor
from xmodule.xml_module import is_pointer_tag, name_to_pathname, deserialize_field
from xmodule.modulestore import Location
from xblock.fields import Scope, String, Boolean, List, Integer, ScopeIds
from xmodule.fields import RelativeTime

from xmodule.modulestore.inheritance import InheritanceKeyValueStore
from xblock.runtime import DbModel
log = logging.getLogger(__name__)


class VideoFields(object):
    """Fields for `VideoModule` and `VideoDescriptor`."""
    display_name = String(
        display_name="Nome Exibido", help="Nome de identificação deste módulo.",
        default="Video",
        scope=Scope.settings
    )
    position = Integer(
        help="Posição atual no vídeo",
        scope=Scope.user_state,
        default=0
    )
    show_captions = Boolean(
        help="Isto controla se as legendas devem ser exibidas ou não por padrão.",
        display_name="Exibir Legenda",
        scope=Scope.settings,
        default=True
    )
    # TODO: This should be moved to Scope.content, but this will
    # require data migration to support the old video module.
    youtube_id_1_0 = String(
        help="Este é o ID de referência do Youtube para vídeo em velocidade normal.",
        display_name="ID Youtube",
        scope=Scope.settings,
        default="OEoXaMPEzfM"
    )
    youtube_id_0_75 = String(
        help="Opcional, para navegadores antigos: ID do Youtube para vídeo em velocidade .75x.",
        display_name="ID Youtube para velocidade .75x",
        scope=Scope.settings,
        default=""
    )
    youtube_id_1_25 = String(
        help="Opcional, para navegadores antigos: ID do Youtube para vídeo em velocidade 1.25x.",
        display_name="ID Youtube para velocidade 1.25x",
        scope=Scope.settings,
        default=""
    )
    youtube_id_1_5 = String(
        help="Opcional, para navegadores antigos: ID do Youtube para vídeo em velocidade 1.5x.",
        display_name="ID Youtube para velocidade 1.5x",
        scope=Scope.settings,
        default=""
    )
    start_time = RelativeTime(  # datetime.timedelta object
        help="Tempo de início do vídeo (HH:MM:SS).",
        display_name="Tempo de Início",
        scope=Scope.settings,
        default=datetime.timedelta(seconds=0)
    )
    end_time = RelativeTime(  # datetime.timedelta object
        help="Tempo de término do vídeo (HH:MM:SS).",
        display_name="Tempo de Término",
        scope=Scope.settings,
        default=datetime.timedelta(seconds=0)
    )
    #front-end code of video player checks logical validity of (start_time, end_time) pair.

    source = String(
        help="URL externa para baixar o vídeo. Isto será exibido como link abaixo do vídeo.",
        display_name="Baixar Vídeo",
        scope=Scope.settings,
        default=""
    )
    html5_sources = List(
        help="Lista de arquivos a serem utilizado com o vídeo HTML5. O primeiro formato de arquivo suportado será exibido.",
        display_name="Fontes de Vídeo",
        scope=Scope.settings,
    )
    track = String(
        help="URL externa para baixar a trilha de legenda. Isto será exibido como link abaixo do vídeo.",
        display_name="Baixar Legenda",
        scope=Scope.settings,
        default=""
    )
    sub = String(
        help="Nome da faixa de legenda (para vídeos que não sejam do Youtube).",
        display_name="Legenda HTML5",
        scope=Scope.settings,
        default=""
    )


class VideoModule(VideoFields, XModule):
    """
    XML source example:

        <video show_captions="true"
            youtube="0.75:jNCf2gIqpeE,1.0:ZwkTiUPN0mg,1.25:rsq9auxASqI,1.50:kMyNdzVHHgg"
            url_name="lecture_21_3" display_name="S19V3: Vacancies"
        >
            <source src=".../mit-3091x/M-3091X-FA12-L21-3_100.mp4"/>
            <source src=".../mit-3091x/M-3091X-FA12-L21-3_100.webm"/>
            <source src=".../mit-3091x/M-3091X-FA12-L21-3_100.ogv"/>
        </video>
    """
    video_time = 0
    icon_class = 'video'

    js = {
        'js': [
            resource_string(__name__, 'js/src/video/00_resizer.js'),
            resource_string(__name__, 'js/src/video/01_initialize.js'),
            resource_string(__name__, 'js/src/video/025_focus_grabber.js'),
            resource_string(__name__, 'js/src/video/02_html5_video.js'),
            resource_string(__name__, 'js/src/video/03_video_player.js'),
            resource_string(__name__, 'js/src/video/04_video_control.js'),
            resource_string(__name__, 'js/src/video/05_video_quality_control.js'),
            resource_string(__name__, 'js/src/video/06_video_progress_slider.js'),
            resource_string(__name__, 'js/src/video/07_video_volume_control.js'),
            resource_string(__name__, 'js/src/video/08_video_speed_control.js'),
            resource_string(__name__, 'js/src/video/09_video_caption.js'),
            resource_string(__name__, 'js/src/video/10_main.js')
        ]
    }
    css = {'scss': [resource_string(__name__, 'css/video/display.scss')]}
    js_module_name = "Video"

    def handle_ajax(self, dispatch, data):
        """This is not being called right now and we raise 404 error."""
        log.debug(u"GET {0}".format(data))
        log.debug(u"DISPATCH {0}".format(dispatch))
        raise Http404()

    def get_html(self):
        caption_asset_path = "/static/subs/"

        get_ext = lambda filename: filename.rpartition('.')[-1]
        sources = {get_ext(src): src for src in self.html5_sources}
        sources['main'] = self.source

        # for testing Youtube timeout in acceptance tests
        if getattr(settings, 'VIDEO_PORT', None):
            yt_test_url = "http://127.0.0.1:" + str(settings.VIDEO_PORT) + '/test_youtube/'
        else:
            yt_test_url = 'https://gdata.youtube.com/feeds/api/videos/'

        return self.system.render_template('video.html', {
            'youtube_streams': _create_youtube_string(self),
            'id': self.location.html_id(),
            'sub': self.sub,
            'sources': sources,
            'track': self.track,
            'display_name': self.display_name_with_default,
            # This won't work when we move to data that
            # isn't on the filesystem
            'data_dir': getattr(self, 'data_dir', None),
            'caption_asset_path': caption_asset_path,
            'show_captions': json.dumps(self.show_captions),
            'start': self.start_time.total_seconds(),
            'end': self.end_time.total_seconds(),
            'autoplay': settings.MITX_FEATURES.get('AUTOPLAY_VIDEOS', False),
            # TODO: Later on the value 1500 should be taken from some global
            # configuration setting field.
            'yt_test_timeout': 1500,
            'yt_test_url': yt_test_url
        })


class VideoDescriptor(VideoFields, TabsEditingDescriptor, EmptyDataRawDescriptor):
    """Descriptor for `VideoModule`."""
    module_class = VideoModule

    tabs = [
        {
            'name': "Basico",
            'template': "video/transcripts.html",
            'current': True
        },
        {
            'name': "Avancado",
            'template': "tabs/metadata-edit-tab.html"
        }
    ]

    def __init__(self, *args, **kwargs):
        super(VideoDescriptor, self).__init__(*args, **kwargs)
        # For backwards compatibility -- if we've got XML data, parse
        # it out and set the metadata fields
        if self.data:
            field_data = self._parse_video_xml(self.data)
            self._field_data.set_many(self, field_data)
            del self.data

    @classmethod
    def from_xml(cls, xml_data, system, org=None, course=None):
        """
        Creates an instance of this descriptor from the supplied xml_data.
        This may be overridden by subclasses

        xml_data: A string of xml that will be translated into data and children for
            this module
        system: A DescriptorSystem for interacting with external resources
        org and course are optional strings that will be used in the generated modules
            url identifiers
        """
        xml_object = etree.fromstring(xml_data)
        url_name = xml_object.get('url_name', xml_object.get('slug'))
        location = Location(
            'i4x', org, course, 'video', url_name
        )
        if is_pointer_tag(xml_object):
            filepath = cls._format_filepath(xml_object.tag, name_to_pathname(url_name))
            xml_data = etree.tostring(cls.load_file(filepath, system.resources_fs, location))
        field_data = cls._parse_video_xml(xml_data)
        field_data['location'] = location
        kvs = InheritanceKeyValueStore(initial_values=field_data)
        field_data = DbModel(kvs)
        video = system.construct_xblock_from_class(
            cls,
            # We're loading a descriptor, so student_id is meaningless
            # We also don't have separate notions of definition and usage ids yet,
            # so we use the location for both
            ScopeIds(None, location.category, location, location),
            field_data,
        )
        return video

    def definition_to_xml(self, resource_fs):
        """
        Returns an xml string representing this module.
        """
        xml = etree.Element('video')
        youtube_string = _create_youtube_string(self)
        # Mild workaround to ensure that tests pass -- if a field
        # is set to its default value, we don't need to write it out.
        if youtube_string and youtube_string != '1.00:OEoXaMPEzfM':
            xml.set('youtube', unicode(youtube_string))
        xml.set('url_name', self.url_name)
        attrs = {
            'display_name': self.display_name,
            'show_captions': json.dumps(self.show_captions),
            'start_time': self.start_time,
            'end_time': self.end_time,
            'sub': self.sub,
        }
        for key, value in attrs.items():
            # Mild workaround to ensure that tests pass -- if a field
            # is set to its default value, we don't write it out.
            if value:
                if key in self.fields and self.fields[key].is_set_on(self):
                    xml.set(key, unicode(value))

        for source in self.html5_sources:
            ele = etree.Element('source')
            ele.set('src', source)
            xml.append(ele)

        if self.track:
            ele = etree.Element('track')
            ele.set('src', self.track)
            xml.append(ele)
        return xml

    def get_context(self):
        """
        Extend context by data for transcripts basic tab.
        """
        _context = super(VideoDescriptor, self).get_context()

        metadata_fields = copy.deepcopy(self.editable_metadata_fields)

        display_name = metadata_fields['display_name']
        video_url = metadata_fields['html5_sources']
        youtube_id_1_0 = metadata_fields['youtube_id_1_0']

        def get_youtube_link(video_id):
            if video_id:
                return 'http://youtu.be/{0}'.format(video_id)
            else:
                return ''

        video_url.update({
            'help': _('URL do YouTube ou link para um arquivo hospedado em algum local da web.'),
            'display_name': 'URL do Vídeo',
            'field_name': 'video_url',
            'type': 'VideoList',
            'default_value': [get_youtube_link(youtube_id_1_0['default_value'])]
        })

        youtube_id_1_0_value = get_youtube_link(youtube_id_1_0['value'])

        if youtube_id_1_0_value:
            video_url['value'].insert(0, youtube_id_1_0_value)

        metadata = {
            'display_name': display_name,
            'video_url': video_url
        }

        _context.update({'transcripts_basic_tab_metadata': metadata})
        return _context

    @classmethod
    def _parse_youtube(cls, data):
        """
        Parses a string of Youtube IDs such as "1.0:AXdE34_U,1.5:VO3SxfeD"
        into a dictionary. Necessary for backwards compatibility with
        XML-based courses.
        """
        ret = {'0.75': '', '1.00': '', '1.25': '', '1.50': ''}

        videos = data.split(',')
        for video in videos:
            pieces = video.split(':')
            try:
                speed = '%.2f' % float(pieces[0])  # normalize speed

                # Handle the fact that youtube IDs got double-quoted for a period of time.
                # Note: we pass in "VideoFields.youtube_id_1_0" so we deserialize as a String--
                # it doesn't matter what the actual speed is for the purposes of deserializing.
                youtube_id = deserialize_field(cls.youtube_id_1_0, pieces[1])
                ret[speed] = youtube_id
            except (ValueError, IndexError):
                log.warning('Invalid YouTube ID: %s' % video)
        return ret

    @classmethod
    def _parse_video_xml(cls, xml_data):
        """
        Parse video fields out of xml_data. The fields are set if they are
        present in the XML.
        """
        xml = etree.fromstring(xml_data)
        field_data = {}

        # Convert between key types for certain attributes --
        # necessary for backwards compatibility.
        conversions = {
            # example: 'start_time': cls._example_convert_start_time
        }

        # Convert between key names for certain attributes --
        # necessary for backwards compatibility.
        compat_keys = {
            'from': 'start_time',
            'to': 'end_time'
        }

        sources = xml.findall('source')
        if sources:
            field_data['html5_sources'] = [ele.get('src') for ele in sources]
            field_data['source'] = field_data['html5_sources'][0]

        track = xml.find('track')
        if track is not None:
            field_data['track'] = track.get('src')

        for attr, value in xml.items():
            if attr in compat_keys:
                attr = compat_keys[attr]
            if attr in cls.metadata_to_strip + ('url_name', 'name'):
                continue
            if attr == 'youtube':
                speeds = cls._parse_youtube(value)
                for speed, youtube_id in speeds.items():
                    # should have made these youtube_id_1_00 for
                    # cleanliness, but hindsight doesn't need glasses
                    normalized_speed = speed[:-1] if speed.endswith('0') else speed
                    # If the user has specified html5 sources, make sure we don't use the default video
                    if youtube_id != '' or 'html5_sources' in field_data:
                        field_data['youtube_id_{0}'.format(normalized_speed.replace('.', '_'))] = youtube_id
            else:
                #  Convert XML attrs into Python values.
                if attr in conversions:
                    value = conversions[attr](value)
                else:
                # We export values with json.dumps (well, except for Strings, but
                # for about a month we did it for Strings also).
                    value = deserialize_field(cls.fields[attr], value)
                field_data[attr] = value

        return field_data


def _create_youtube_string(module):
    """
    Create a string of Youtube IDs from `module`'s metadata
    attributes. Only writes a speed if an ID is present in the
    module.  Necessary for backwards compatibility with XML-based
    courses.
    """
    youtube_ids = [
        module.youtube_id_0_75,
        module.youtube_id_1_0,
        module.youtube_id_1_25,
        module.youtube_id_1_5
    ]
    youtube_speeds = ['0.75', '1.00', '1.25', '1.50']
    return ','.join([':'.join(pair)
                     for pair
                     in zip(youtube_speeds, youtube_ids)
                     if pair[1]])
