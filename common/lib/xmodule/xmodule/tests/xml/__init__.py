"""
Xml parsing tests for XModules
"""
import pprint
from mock import Mock
from unittest import TestCase

from xmodule.x_module import XMLParsingSystem, policy_key
from xmodule.mako_module import MakoDescriptorSystem
from xmodule.modulestore.xml import create_block_from_xml, CourseLocationGenerator
from xmodule.modulestore.locations import SlashSeparatedCourseKey, Location

from xblock.runtime import KvsFieldData, DictKeyValueStore


class InMemorySystem(XMLParsingSystem, MakoDescriptorSystem):  # pylint: disable=abstract-method
    """
    The simplest possible XMLParsingSystem
    """
    def __init__(self, xml_import_data):
        self.course_id = SlashSeparatedCourseKey.from_deprecated_string(xml_import_data.course_id)
        self.default_class = xml_import_data.default_class
        self._descriptors = {}

        def get_policy(usage_id):
            """Return the policy data for the specified usage"""
            return xml_import_data.policy.get(policy_key(usage_id), {})

        super(InMemorySystem, self).__init__(
            get_policy=get_policy,
            process_xml=self.process_xml,
            load_item=self.load_item,
            error_tracker=Mock(),
            resources_fs=xml_import_data.filesystem,
            mixins=xml_import_data.xblock_mixins,
            select=xml_import_data.xblock_select,
            render_template=lambda template, context: pprint.pformat((template, context)),
            field_data=KvsFieldData(DictKeyValueStore()),
        )

    def process_xml(self, xml):  # pylint: disable=method-hidden
        """Parse `xml` as an XBlock, and add it to `self._descriptors`"""
        descriptor = create_block_from_xml(
            xml,
            self,
            CourseLocationGenerator(self.course_id),
        )
        self._descriptors[descriptor.location.url()] = descriptor
        return descriptor

    def load_item(self, location):  # pylint: disable=method-hidden
        """Return the descriptor loaded for `location`"""
        return self._descriptors[location.url()]


class XModuleXmlImportTest(TestCase):
    """Base class for tests that use basic XML parsing"""
    def process_xml(self, xml_import_data):
        """Use the `xml_import_data` to import an :class:`XBlock` from XML."""
        system = InMemorySystem(xml_import_data)
        return system.process_xml(xml_import_data.xml_string)
