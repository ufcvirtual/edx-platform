# disable missing docstring
# pylint: disable=C0111

from lettuce import world, step
from component_settings_editor_helpers import enter_xml_in_advanced_problem
from nose.tools import assert_true, assert_equal
from xmodule.modulestore.locations import SlashSeparatedCourseKey
from django.core.urlresolvers import reverse


@step('I export the course$')
def i_export_the_course(step):
    world.click_tools()
    link_css = 'li.nav-course-tools-export a'
    world.css_click(link_css)
    world.css_click('a.action-export')


@step('I edit and enter bad XML$')
def i_enter_bad_xml(step):
    enter_xml_in_advanced_problem(step,
        """<problem><h1>Smallest Canvas</h1>
            <p>You want to make the smallest canvas you can.</p>
            <multiplechoiceresponse>
            <choicegroup type="MultipleChoice">
              <choice correct="false"><verbatim><canvas id="myCanvas" width = 10 height = 100> </canvas></verbatim></choice>
              <choice correct="true"><code><canvas id="myCanvas" width = 10 height = 10> </canvas></code></choice>
            </choicegroup>
            </multiplechoiceresponse>
            </problem>"""
    )


@step('I edit and enter an ampersand$')
def i_enter_bad_xml(step):
    enter_xml_in_advanced_problem(step, "<problem>&</problem>")


@step('I get an error dialog$')
def get_an_error_dialog(step):
    assert_true(world.is_css_present("div.prompt.error"))


@step('I can click to go to the unit with the error$')
def i_click_on_error_dialog(step):
    world.click_link_by_text('Correct failed component')
    assert_true(world.css_html("span.inline-error").startswith("Problem i4x://MITx/999/problem"))
    course_key = SlashSeparatedCourseKey("MITx", "999", "Robot_Super_Course")
    # Unfortunately we don't know the actual ID of the vertical. So we will need to strip off "dummy_id"
    # and just check that we did go to a vertical page in the course (there should only be one).
    vertical_usage_key = course_key.make_usage_key("vertical", "dummy_id")
    vertical_url = reverse('contentstore.views.unit_handler', kwargs={'usage_key_string': unicode(vertical_usage_key)})
    vertical_url = vertical_url.replace("dummy_id", "")
    assert_equal(1, world.browser.url.count(vertical_url))
