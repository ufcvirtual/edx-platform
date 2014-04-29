# encoding: utf-8
"""


verify_student/start?course_id=MITx/6.002x/2013_Spring # create
              /upload_face?course_id=MITx/6.002x/2013_Spring
              /upload_photo_id
              /confirm # mark_ready()

 ---> To Payment

"""
import urllib
from mock import patch, Mock
import pytz
from datetime import timedelta, datetime

from django.test import TestCase
from django.test.utils import override_settings
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

from mock import sentinel

from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.locations import SlashSeparatedCourseKey
from courseware.tests.tests import TEST_DATA_MONGO_MODULESTORE
from student.tests.factories import UserFactory
from student.models import CourseEnrollment
from course_modes.models import CourseMode
from verify_student.views import render_to_response
from verify_student.models import SoftwareSecurePhotoVerification
from reverification.tests.factories import MidcourseReverificationWindowFactory


def mock_render_to_response(*args, **kwargs):
    return render_to_response(*args, **kwargs)

render_mock = Mock(side_effect=mock_render_to_response)


class StartView(TestCase):

    def start_url(self, course_id=""):
        return "/verify_student/{0}".format(urllib.quote(course_id))

    def test_start_new_verification(self):
        """
        Test the case where the user has no pending `PhotoVerficiationAttempts`,
        but is just starting their first.
        """
        user = UserFactory.create(username="rusty", password="test")
        self.client.login(username="rusty", password="test")

    def must_be_logged_in(self):
        self.assertHttpForbidden(self.client.get(self.start_url()))


@override_settings(MODULESTORE=TEST_DATA_MONGO_MODULESTORE)
class TestVerifyView(TestCase):
    def setUp(self):
        self.user = UserFactory.create(username="rusty", password="test")
        self.client.login(username="rusty", password="test")
        self.course_key = SlashSeparatedCourseKey('Robot', '999', 'Test_Course')
        CourseFactory.create(org='Robot', number='999', display_name='Test Course')
        verified_mode = CourseMode(course_id=self.course_key,
                                   mode_slug="verified",
                                   mode_display_name="Verified Certificate",
                                   min_price=50)
        verified_mode.save()

    def test_invalid_course(self):
        fake_course_id = "Robot/999/Fake_Course"
        url = reverse('verify_student_verify',
                      kwargs={"course_id": fake_course_id})
        response = self.client.get(url)

        self.assertEquals(response.status_code, 302)


@override_settings(MODULESTORE=TEST_DATA_MONGO_MODULESTORE)
class TestReverifyView(TestCase):
    """
    Tests for the reverification views

    """
    def setUp(self):
        self.user = UserFactory.create(username="rusty", password="test")
        self.client.login(username="rusty", password="test")
        self.course = CourseFactory.create(org='MITx', number='999', display_name='Robot Super Course')
        self.course_key = self.course.id

    @patch('verify_student.views.render_to_response', render_mock)
    def test_reverify_get(self):
        url = reverse('verify_student_reverify')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        ((_template, context), _kwargs) = render_mock.call_args
        self.assertFalse(context['error'])

    @patch('verify_student.views.render_to_response', render_mock)
    def test_reverify_post_failure(self):
        url = reverse('verify_student_reverify')
        response = self.client.post(url, {'face_image': '',
                                          'photo_id_image': ''})
        self.assertEquals(response.status_code, 200)
        ((template, context), _kwargs) = render_mock.call_args
        self.assertIn('photo_reverification', template)
        self.assertTrue(context['error'])

    @patch.dict(settings.FEATURES, {'AUTOMATIC_VERIFY_STUDENT_IDENTITY_FOR_TESTING': True})
    def test_reverify_post_success(self):
        url = reverse('verify_student_reverify')
        response = self.client.post(url, {'face_image': ',',
                                          'photo_id_image': ','})
        self.assertEquals(response.status_code, 302)
        try:
            verification_attempt = SoftwareSecurePhotoVerification.objects.get(user=self.user)
            self.assertIsNotNone(verification_attempt)
        except ObjectDoesNotExist:
            self.fail('No verification object generated')
        ((template, context), _kwargs) = render_mock.call_args
        self.assertIn('photo_reverification', template)
        self.assertTrue(context['error'])


@override_settings(MODULESTORE=TEST_DATA_MONGO_MODULESTORE)
class TestMidCourseReverifyView(TestCase):
    """ Tests for the midcourse reverification views """
    def setUp(self):
        self.user = UserFactory.create(username="rusty", password="test")
        self.client.login(username="rusty", password="test")
        course_id = 'Robot/999/Test_Course'
        self.course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
        CourseFactory.create(org='Robot', number='999', display_name='Test Course')

        patcher = patch('student.models.server_track')
        self.mock_server_track = patcher.start()
        self.addCleanup(patcher.stop)

        crum_patcher = patch('student.models.crum.get_current_request')
        self.mock_get_current_request = crum_patcher.start()
        self.addCleanup(crum_patcher.stop)
        self.mock_get_current_request.return_value = sentinel.request

    @patch('verify_student.views.render_to_response', render_mock)
    def test_midcourse_reverify_get(self):
        url = reverse('verify_student_midcourse_reverify',
                      kwargs={"course_id": self.course_key.to_deprecated_string()})
        response = self.client.get(url)

        # Check that user entering the reverify flow was logged
        self.mock_server_track.assert_called_once_with(
            sentinel.request,
            'edx.course.enrollment.reverify.started',
            {
                'user_id': self.user.id,
                'course_id': self.course_key.to_deprecated_string(),
                'mode': "verified",
            }
        )
        self.mock_server_track.reset_mock()

        self.assertEquals(response.status_code, 200)
        ((_template, context), _kwargs) = render_mock.call_args
        self.assertFalse(context['error'])

    @patch.dict(settings.FEATURES, {'AUTOMATIC_VERIFY_STUDENT_IDENTITY_FOR_TESTING': True})
    def test_midcourse_reverify_post_success(self):
        window = MidcourseReverificationWindowFactory(course_id=self.course_key)
        url = reverse('verify_student_midcourse_reverify', kwargs={'course_id': self.course_key.to_deprecated_string()})

        response = self.client.post(url, {'face_image': ','})

        # Check that submission event was logged
        self.mock_server_track.assert_called_once_with(
            sentinel.request,
            'edx.course.enrollment.reverify.submitted',
            {
                'user_id': self.user.id,
                'course_id': self.course_key.to_deprecated_string(),
                'mode': "verified",
            }
        )
        self.mock_server_track.reset_mock()

        self.assertEquals(response.status_code, 302)
        try:
            verification_attempt = SoftwareSecurePhotoVerification.objects.get(user=self.user, window=window)
            self.assertIsNotNone(verification_attempt)
        except ObjectDoesNotExist:
            self.fail('No verification object generated')

    @patch.dict(settings.FEATURES, {'AUTOMATIC_VERIFY_STUDENT_IDENTITY_FOR_TESTING': True})
    def test_midcourse_reverify_post_failure_expired_window(self):
        window = MidcourseReverificationWindowFactory(
            course_id=self.course_key,
            start_date=datetime.now(pytz.UTC) - timedelta(days=100),
            end_date=datetime.now(pytz.UTC) - timedelta(days=50),
        )
        url = reverse('verify_student_midcourse_reverify', kwargs={'course_id': self.course_key.to_deprecated_string()})
        response = self.client.post(url, {'face_image': ','})
        self.assertEquals(response.status_code, 302)
        with self.assertRaises(ObjectDoesNotExist):
            SoftwareSecurePhotoVerification.objects.get(user=self.user, window=window)

    @patch('verify_student.views.render_to_response', render_mock)
    def test_midcourse_reverify_dash(self):
        url = reverse('verify_student_midcourse_reverify_dash')
        response = self.client.get(url)
        # not enrolled in any courses
        self.assertEquals(response.status_code, 200)

        enrollment = CourseEnrollment.get_or_create_enrollment(self.user, self.course_key)
        enrollment.update_enrollment(mode="verified", is_active=True)
        MidcourseReverificationWindowFactory(course_id=self.course_key)
        response = self.client.get(url)
        # enrolled in a verified course, and the window is open
        self.assertEquals(response.status_code, 200)


@override_settings(MODULESTORE=TEST_DATA_MONGO_MODULESTORE)
class TestReverificationBanner(TestCase):
    """ Tests for the midcourse reverification  failed toggle banner off """

    @patch.dict(settings.FEATURES, {'AUTOMATIC_VERIFY_STUDENT_IDENTITY_FOR_TESTING': True})
    def setUp(self):
        self.user = UserFactory.create(username="rusty", password="test")
        self.client.login(username="rusty", password="test")
        self.course_id = 'Robot/999/Test_Course'
        CourseFactory.create(org='Robot', number='999', display_name=u'Test Course é')
        self.window = MidcourseReverificationWindowFactory(course_id=self.course_id)
        url = reverse('verify_student_midcourse_reverify', kwargs={'course_id': self.course_id})
        self.client.post(url, {'face_image': ','})
        photo_verification = SoftwareSecurePhotoVerification.objects.get(user=self.user, window=self.window)
        photo_verification.status = 'denied'
        photo_verification.save()

    def test_banner_display_off(self):
        self.client.post(reverse('verify_student_toggle_failed_banner_off'))
        photo_verification = SoftwareSecurePhotoVerification.objects.get(user=self.user, window=self.window)
        self.assertFalse(photo_verification.display)
