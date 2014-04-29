"""
Define common steps for instructor dashboard acceptance tests.
"""

# pylint: disable=C0111
# pylint: disable=W0621

from __future__ import absolute_import

from django.conf import settings
from lettuce import world, step
from mock import patch
from nose.tools import assert_in  # pylint: disable=E0611

from courseware.tests.factories import StaffFactory, InstructorFactory


@step(u'Given I am "([^"]*)" for a very large course')
def make_staff_or_instructor_for_large_course(step, role):
    make_large_course(step, role)


@patch.dict('courseware.access.settings.FEATURES', {"MAX_ENROLLMENT_INSTR_BUTTONS": 0})
def make_large_course(step, role):
    i_am_staff_or_instructor(step, role)


@step(u'Given I am "([^"]*)" for a course')
def i_am_staff_or_instructor(step, role):  # pylint: disable=unused-argument
    ## In summary: makes a test course, makes a new Staff or Instructor user
    ## (depending on `role`), and logs that user in to the course

    # Store the role
    assert_in(role, ['instructor', 'staff'])

    # Clear existing courses to avoid conflicts
    world.clear_courses()

    # Create a new course
    course = world.CourseFactory.create(
        org='edx',
        number='999',
        display_name='Test Course'
    )

    world.course_id = course.id
    world.role = 'instructor'
    # Log in as the an instructor or staff for the course
    if role == 'instructor':
        # Make & register an instructor for the course
        world.instructor = InstructorFactory(course=world.course_id)
        world.enroll_user(world.instructor, world.course_id)

        world.log_in(
            username=world.instructor.username,
            password='test',
            email=world.instructor.email,
            name=world.instructor.profile.name
        )

    else:
        world.role = 'staff'
        # Make & register a staff member
        world.staff = StaffFactory(course=world.course_id)
        world.enroll_user(world.staff, world.course_id)

        world.log_in(
            username=world.staff.username,
            password='test',
            email=world.staff.email,
            name=world.staff.profile.name
        )


def go_to_section(section_name):
    # section name should be one of
    # course_info, membership, student_admin, data_download, analytics, send_email
    world.visit('/courses/edx/999/Test_Course')
    world.css_click('a[href="/courses/edx/999/Test_Course/instructor"]')
    world.css_click('div.beta-button-wrapper>a.beta-button')
    world.css_click('a[data-section="{0}"]'.format(section_name))


@step(u'I click "([^"]*)"')
def click_a_button(step, button):  # pylint: disable=unused-argument

    if button == "Generate Grade Report":
        # Go to the data download section of the instructor dash
        go_to_section("data_download")

        # Click generate grade report button
        world.css_click('input[name="calculate-grades-csv"]')

        # Expect to see a message that grade report is being generated
        expected_msg = "Your grade report is being generated! You can view the status of the generation task in the 'Pending Instructor Tasks' section."
        world.wait_for_visible('#grade-request-response')
        assert_in(
            expected_msg, world.css_text('#grade-request-response'),
            msg="Could not find grade report generation success message."
        )

    elif button == "Grading Configuration":
        # Go to the data download section of the instructor dash
        go_to_section("data_download")

        world.css_click('input[name="dump-gradeconf"]')

    elif button == "List enrolled students' profile information":
        # Go to the data download section of the instructor dash
        go_to_section("data_download")

        world.css_click('input[name="list-profiles"]')

    elif button == "Download profile information as a CSV":
        # Go to the data download section of the instructor dash
        go_to_section("data_download")
        # Don't do anything else, next step will handle clicking & downloading

    else:
        raise ValueError("Unrecognized button option " + button)


@step(u'I visit the "([^"]*)" tab')
def click_a_button(step, tab_name):  # pylint: disable=unused-argument
    # course_info, membership, student_admin, data_download, analytics, send_email
    tab_name_dict = {
        'Course Info': 'course_info',
        'Membership': 'membership',
        'Student Admin': 'student_admin',
        'Data Download': 'data_download',
        'Analytics': 'analytics',
        'Email': 'send_email',
    }
    go_to_section(tab_name_dict[tab_name])
