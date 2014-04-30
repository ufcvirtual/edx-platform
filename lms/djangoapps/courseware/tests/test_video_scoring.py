# -*- coding: utf-8 -*-
"""Video xmodule tests in mongo."""
import json
import unittest
from collections import OrderedDict
from mock import patch, PropertyMock, MagicMock

from django.conf import settings

from xblock.fields import ScopeIds
from xblock.field_data import DictFieldData

from xmodule.video_module import create_youtube_string
from xmodule.tests import get_test_descriptor_system
from xmodule.modulestore import Location
from xmodule.video_module import VideoDescriptor

from . import BaseTestXmodule
from .test_video_xml import SOURCE_XML
from .test_video_handlers import TestVideo


class TestVideoScoring(BaseTestXmodule):

    CATEGORY = "video"
    DATA = SOURCE_XML
    METADATA = {}

    def setUp(self):
        self.setup_course()

    def test_maxscore(self):
        self.initialize_module()
        self.item_descriptor.render('student_view')
        self.item = self.item_descriptor.xmodule_runtime.xmodule_instance
        self.assertEqual(self.item.max_score(), None)

    def test_update_score(self):
        self.initialize_module()
        self.initialize_module()
        self.item_descriptor.render('student_view')
        self.item = self.item_descriptor.xmodule_runtime.xmodule_instance

        with self.assertRaises(NotImplementedError):
            self.item.update_score(0.5)

        # TODO: mock get_real_user and system publish here and check of updated module score.

    def test_graders_only_has_score(self):
        metadata = {
            'has_score': True,
        }
        self.initialize_module(metadata=metadata)
        self.item_descriptor.render('student_view')
        self.item = self.item_descriptor.xmodule_runtime.xmodule_instance
        self.assertEqual(self.item.max_score(), self.item.weight)
        self.assertEqual(self.item.graders(), '{}')

    def test_graders(self):
        metadata = {
            'has_score': True,
            'scored_on_end': True,
            'scored_on_percent': 75,
        }
        self.initialize_module(metadata=metadata)
        self.item_descriptor.render('student_view')
        self.item = self.item_descriptor.xmodule_runtime.xmodule_instance
        self.assertEqual(self.item.max_score(), self.item.weight)
        self.assertDictEqual(
            json.loads(self.item.graders()),
            {
                'scored_on_end': [False, True],
                'scored_on_percent': [False, 75]
            }
        )

