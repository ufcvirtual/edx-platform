"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from datetime import datetime, timedelta
import pytz

from xmodule.modulestore.locations import SlashSeparatedCourseKey
from django.test import TestCase
from course_modes.models import CourseMode, Mode


class CourseModeModelTest(TestCase):
    """
    Tests for the CourseMode model
    """

    def setUp(self):
        self.course_id = SlashSeparatedCourseKey('Test', 'TestCourse', 'TestCourseRun')
        CourseMode.objects.all().delete()

    def create_mode(self, mode_slug, mode_name, min_price=0, suggested_prices='', currency='usd'):
        """
        Create a new course mode
        """
        return CourseMode.objects.get_or_create(
            course_id=self.course_id,
            mode_display_name=mode_name,
            mode_slug=mode_slug,
            min_price=min_price,
            suggested_prices=suggested_prices,
            currency=currency,
        )

    def test_modes_for_course_empty(self):
        """
        If we can't find any modes, we should get back the default mode
        """
        # shouldn't be able to find a corresponding course
        modes = CourseMode.modes_for_course(self.course_id)
        self.assertEqual([CourseMode.DEFAULT_MODE], modes)

    def test_nodes_for_course_single(self):
        """
        Find the modes for a course with only one mode
        """

        self.create_mode('verified', 'Verified Certificate')
        modes = CourseMode.modes_for_course(self.course_id)
        mode = Mode(u'verified', u'Verified Certificate', 0, '', 'usd', None)
        self.assertEqual([mode], modes)

        modes_dict = CourseMode.modes_for_course_dict(self.course_id)
        self.assertEqual(modes_dict['verified'], mode)
        self.assertEqual(CourseMode.mode_for_course(self.course_id, 'verified'),
                         mode)

    def test_modes_for_course_multiple(self):
        """
        Finding the modes when there's multiple modes
        """
        mode1 = Mode(u'honor', u'Honor Code Certificate', 0, '', 'usd', None)
        mode2 = Mode(u'verified', u'Verified Certificate', 0, '', 'usd', None)
        set_modes = [mode1, mode2]
        for mode in set_modes:
            self.create_mode(mode.slug, mode.name, mode.min_price, mode.suggested_prices)

        modes = CourseMode.modes_for_course(self.course_id)
        self.assertEqual(modes, set_modes)
        self.assertEqual(mode1, CourseMode.mode_for_course(self.course_id, u'honor'))
        self.assertEqual(mode2, CourseMode.mode_for_course(self.course_id, u'verified'))
        self.assertIsNone(CourseMode.mode_for_course(self.course_id, 'DNE'))

    def test_min_course_price_for_currency(self):
        """
        Get the min course price for a course according to currency
        """
        # no modes, should get 0
        self.assertEqual(0, CourseMode.min_course_price_for_currency(self.course_id, 'usd'))

        # create some modes
        mode1 = Mode(u'honor', u'Honor Code Certificate', 10, '', 'usd', None)
        mode2 = Mode(u'verified', u'Verified Certificate', 20, '', 'usd', None)
        mode3 = Mode(u'honor', u'Honor Code Certificate', 80, '', 'cny', None)
        set_modes = [mode1, mode2, mode3]
        for mode in set_modes:
            self.create_mode(mode.slug, mode.name, mode.min_price, mode.suggested_prices, mode.currency)

        self.assertEqual(10, CourseMode.min_course_price_for_currency(self.course_id, 'usd'))
        self.assertEqual(80, CourseMode.min_course_price_for_currency(self.course_id, 'cny'))

    def test_modes_for_course_expired(self):
        expired_mode, _status = self.create_mode('verified', 'Verified Certificate')
        expired_mode.expiration_datetime = datetime.now(pytz.UTC) + timedelta(days=-1)
        expired_mode.save()
        modes = CourseMode.modes_for_course(self.course_id)
        self.assertEqual([CourseMode.DEFAULT_MODE], modes)

        mode1 = Mode(u'honor', u'Honor Code Certificate', 0, '', 'usd', None)
        self.create_mode(mode1.slug, mode1.name, mode1.min_price, mode1.suggested_prices)
        modes = CourseMode.modes_for_course(self.course_id)
        self.assertEqual([mode1], modes)

        expiration_datetime = datetime.now(pytz.UTC) + timedelta(days=1)
        expired_mode.expiration_datetime = expiration_datetime
        expired_mode.save()
        expired_mode_value = Mode(u'verified', u'Verified Certificate', 0, '', 'usd', expiration_datetime)
        modes = CourseMode.modes_for_course(self.course_id)
        self.assertEqual([expired_mode_value, mode1], modes)

        modes = CourseMode.modes_for_course(SlashSeparatedCourseKey('TestCourse', 'Test', 'second_test_course'))
        self.assertEqual([CourseMode.DEFAULT_MODE], modes)
