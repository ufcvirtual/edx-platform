"""
Tests for views/tools.py.
"""

import datetime
import functools
import mock
import json
import unittest

from django.test.utils import override_settings
from django.utils.timezone import utc

from courseware.models import StudentModule
from courseware.tests.modulestore_config import TEST_DATA_MIXED_MODULESTORE
from student.tests.factories import UserFactory
from xmodule.fields import Date
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.keys import CourseKey

from ..views import tools

DATE_FIELD = Date()


class TestDashboardError(unittest.TestCase):
    """
    Test DashboardError exceptions.
    """
    def test_response(self):
        error = tools.DashboardError(u'Oh noes!')
        response = json.loads(error.response().content)
        self.assertEqual(response, {'error': 'Oh noes!'})


class TestHandleDashboardError(unittest.TestCase):
    """
    Test handle_dashboard_error decorator.
    """
    def test_error(self):
        # pylint: disable=W0613
        @tools.handle_dashboard_error
        def view(request, course_id):
            """
            Raises DashboardError.
            """
            raise tools.DashboardError("Oh noes!")

        response = json.loads(view(None, None).content)
        self.assertEqual(response, {'error': 'Oh noes!'})

    def test_no_error(self):
        # pylint: disable=W0613
        @tools.handle_dashboard_error
        def view(request, course_id):
            """
            Returns "Oh yes!"
            """
            return "Oh yes!"

        self.assertEqual(view(None, None), "Oh yes!")


class TestParseDatetime(unittest.TestCase):
    """
    Test date parsing.
    """
    def test_parse_no_error(self):
        self.assertEqual(
            tools.parse_datetime('5/12/2010 2:42'),
            datetime.datetime(2010, 5, 12, 2, 42, tzinfo=utc))

    def test_parse_error(self):
        with self.assertRaises(tools.DashboardError):
            tools.parse_datetime('foo')


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestFindUnit(ModuleStoreTestCase):
    """
    Test the find_unit function.
    """

    def setUp(self):
        """
        Fixtures.
        """
        course = CourseFactory.create()
        week1 = ItemFactory.create()
        homework = ItemFactory.create(parent_location=week1.location)
        week1.children.append(homework.location)
        course.children.append(week1.location)

        self.course = course
        self.homework = homework

    def test_find_unit_success(self):
        """
        Test finding a nested unit.
        """
        url = self.homework.location.url()
        self.assertEqual(tools.find_unit(self.course, url), self.homework)

    def test_find_unit_notfound(self):
        """
        Test attempt to find a unit that does not exist.
        """
        url = "i4x://MITx/999/chapter/notfound"
        with self.assertRaises(tools.DashboardError):
            tools.find_unit(self.course, url)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestGetUnitsWithDueDate(ModuleStoreTestCase):
    """
    Test the get_units_with_due_date function.
    """
    def setUp(self):
        """
        Fixtures.
        """
        due = datetime.datetime(2010, 5, 12, 2, 42, tzinfo=utc)
        course = CourseFactory.create()
        week1 = ItemFactory.create(due=due)
        week2 = ItemFactory.create(due=due)
        course.children = [week1.location.url(), week2.location.url()]

        homework = ItemFactory.create(
            parent_location=week1.location,
            due=due
        )
        week1.children = [homework.location.url()]

        self.course = course
        self.week1 = week1
        self.week2 = week2

    def test_it(self):

        def urls(seq):
            "URLs for sequence of nodes."
            return sorted(i.location.url() for i in seq)

        self.assertEquals(
            urls(tools.get_units_with_due_date(self.course)),
            urls((self.week1, self.week2)))


class TestTitleOrUrl(unittest.TestCase):
    """
    Test the title_or_url funciton.
    """
    def test_title(self):
        unit = mock.Mock(display_name='hello')
        self.assertEquals(tools.title_or_url(unit), 'hello')

    def test_url(self):
        unit = mock.Mock(display_name=None)
        unit.location.url.return_value = 'test:hello'
        self.assertEquals(tools.title_or_url(unit), 'test:hello')


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestSetDueDateExtension(ModuleStoreTestCase):
    """
    Test the set_due_date_extensions function.
    """
    def setUp(self):
        """
        Fixtures.
        """
        due = datetime.datetime(2010, 5, 12, 2, 42, tzinfo=utc)
        course = CourseFactory.create()
        week1 = ItemFactory.create(due=due)
        week2 = ItemFactory.create(due=due)
        course.children = [week1.location.url(), week2.location.url()]

        homework = ItemFactory.create(
            parent_location=week1.location,
            due=due
        )
        week1.children = [homework.location.url()]

        user = UserFactory.create()
        StudentModule(
            state='{}',
            student_id=user.id,
            course_id=course.id,
            module_state_key=week1.location).save()
        StudentModule(
            state='{}',
            student_id=user.id,
            course_id=course.id,
            module_state_key=homework.location).save()

        self.course = course
        self.week1 = week1
        self.homework = homework
        self.week2 = week2
        self.user = user

        self.extended_due = functools.partial(
            get_extended_due, course, student=user)

    def test_set_due_date_extension(self):
        extended = datetime.datetime(2013, 12, 25, 0, 0, tzinfo=utc)
        tools.set_due_date_extension(self.course, self.week1, self.user,
                                     extended)
        self.assertEqual(self.extended_due(self.week1), extended)
        self.assertEqual(self.extended_due(self.homework), extended)

    def test_reset_due_date_extension(self):
        tools.set_due_date_extension(self.course, self.week1, self.user, None)
        self.assertEqual(self.extended_due(self.week1), None)


@override_settings(MODULESTORE=TEST_DATA_MIXED_MODULESTORE)
class TestDataDumps(ModuleStoreTestCase):
    """
    Test data dumps for reporting.
    """

    def setUp(self):
        """
        Fixtures.
        """
        due = datetime.datetime(2010, 5, 12, 2, 42, tzinfo=utc)
        course = CourseFactory.create()
        week1 = ItemFactory.create(due=due)
        week2 = ItemFactory.create(due=due)
        week3 = ItemFactory.create(due=due)
        course.children = [week1.location.url(), week2.location.url(),
                           week3.location.url()]

        homework = ItemFactory.create(
            parent_location=week1.location,
            due=due
        )
        week1.children = [homework.location.url()]

        user1 = UserFactory.create()
        StudentModule(
            state='{}',
            student_id=user1.id,
            course_id=course.id,
            module_state_key=week1.location).save()
        StudentModule(
            state='{}',
            student_id=user1.id,
            course_id=course.id,
            module_state_key=week2.location).save()
        StudentModule(
            state='{}',
            student_id=user1.id,
            course_id=course.id,
            module_state_key=week3.location).save()
        StudentModule(
            state='{}',
            student_id=user1.id,
            course_id=course.id,
            module_state_key=homework.location).save()

        user2 = UserFactory.create()
        StudentModule(
            state='{}',
            student_id=user2.id,
            course_id=course.id,
            module_state_key=week1.location).save()
        StudentModule(
            state='{}',
            student_id=user2.id,
            course_id=course.id,
            module_state_key=homework.location).save()

        user3 = UserFactory.create()
        StudentModule(
            state='{}',
            student_id=user3.id,
            course_id=course.id,
            module_state_key=week1.location).save()
        StudentModule(
            state='{}',
            student_id=user3.id,
            course_id=course.id,
            module_state_key=homework.location).save()

        self.course = course
        self.week1 = week1
        self.homework = homework
        self.week2 = week2
        self.user1 = user1
        self.user2 = user2

    def test_dump_module_extensions(self):
        extended = datetime.datetime(2013, 12, 25, 0, 0, tzinfo=utc)
        tools.set_due_date_extension(self.course, self.week1, self.user1,
                                     extended)
        tools.set_due_date_extension(self.course, self.week1, self.user2,
                                     extended)
        report = tools.dump_module_extensions(self.course, self.week1)
        self.assertEqual(
            report['title'], u'Users with due date extensions for ' +
            self.week1.display_name)
        self.assertEqual(
            report['header'], ["Username", "Full Name", "Extended Due Date"])
        self.assertEqual(report['data'], [
            {"Username": self.user1.username,
             "Full Name": self.user1.profile.name,
             "Extended Due Date": "2013-12-25 00:00"},
            {"Username": self.user2.username,
             "Full Name": self.user2.profile.name,
             "Extended Due Date": "2013-12-25 00:00"}])

    def test_dump_student_extensions(self):
        extended = datetime.datetime(2013, 12, 25, 0, 0, tzinfo=utc)
        tools.set_due_date_extension(self.course, self.week1, self.user1,
                                     extended)
        tools.set_due_date_extension(self.course, self.week2, self.user1,
                                     extended)
        report = tools.dump_student_extensions(self.course, self.user1)
        self.assertEqual(
            report['title'], u'Due date extensions for %s (%s)' %
            (self.user1.profile.name, self.user1.username))
        self.assertEqual(
            report['header'], ["Unit", "Extended Due Date"])
        self.assertEqual(report['data'], [
            {"Unit": self.week1.display_name,
             "Extended Due Date": "2013-12-25 00:00"},
            {"Unit": self.week2.display_name,
             "Extended Due Date": "2013-12-25 00:00"}])


def get_extended_due(course, unit, student):
    """
    Get the extended due date out of a student's state for a particular unit.
    """
    student_module = StudentModule.objects.get(
        student_id=student.id,
        course_id=course.id,
        module_id=unit.location
    )

    state = json.loads(student_module.state)
    extended = state.get('extended_due', None)
    if extended:
        return DATE_FIELD.from_json(extended)


def msk_from_problem_urlname(course_id, urlname, block_type='problem'):
    """
    Convert a 'problem urlname' to a module state key (db field)
    """
    if not isinstance(course_id, CourseKey):
        raise ValueError
    if urlname.endswith(".xml"):
        urlname = urlname[:-4]

    return course_id.make_usage_key(block_type, urlname)
