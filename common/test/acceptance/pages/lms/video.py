"""
Video player in the courseware.
"""

import time
import requests
from selenium.webdriver.common.action_chains import ActionChains
from bok_choy.page_object import PageObject
from bok_choy.promise import EmptyPromise, Promise
from bok_choy.javascript import wait_for_js, js_defined


VIDEO_BUTTONS = {
    'CC': '.hide-subtitles',
    'volume': '.volume',
    'play': '.video_control.play',
    'pause': '.video_control.pause',
    'fullscreen': '.add-fullscreen',
    'download_transcript': '.video-tracks > a',
}

CSS_CLASS_NAMES = {
    'closed_captions': '.closed .subtitles',
    'captions_rendered': '.video.is-captions-rendered',
    'captions': '.subtitles',
    'captions_text': '.subtitles > li',
    'error_message': '.video .video-player h3',
    'video_container': 'div.video',
    'video_sources': '.video-player video source',
    'video_spinner': '.video-wrapper .spinner',
    'video_xmodule': '.xmodule_VideoModule',
    'video_init': '.is-initialized',
    'video_time': 'div.vidtime',
    'video_display_name': '.vert h2'
}

VIDEO_MODES = {
    'html5': 'video',
    'youtube': 'iframe'
}

VIDEO_MENUS = {
    'language': '.lang .menu',
    'speed': '.speed .menu',
    'download_transcript': '.video-tracks .a11y-menu-list',
    'transcript-format': '.video-tracks .a11y-menu-button'
}


@js_defined('window.Video', 'window.RequireJS.require', 'window.jQuery')
class VideoPage(PageObject):
    """
    Video player in the courseware.
    """

    url = None

    @wait_for_js
    def is_browser_on_page(self):
        return self.q(css='div{0}'.format(CSS_CLASS_NAMES['video_xmodule'])).present

    @wait_for_js
    def _wait_for_element(self, element_css_selector, promise_desc):
        """
        Wait for element specified by `element_css_selector` is present in DOM.
        :param element_css_selector: css selector of the element
        :param promise_desc: Description of the Promise, used in log messages.
        :return: BrokenPromise: the `Promise` was not satisfied within the time or attempt limits.
        """

        def _is_element_present():
            """
            Check if web-element present in DOM
            :return: bool
            """
            return self.q(css=element_css_selector).present

        EmptyPromise(_is_element_present, promise_desc, timeout=200).fulfill()

    @wait_for_js
    def wait_for_video_class(self):
        """
        Wait until element with class name `video` appeared in DOM.
        """
        self.wait_for_ajax()

        video_css = '{0}'.format(CSS_CLASS_NAMES['video_container'])
        self._wait_for_element(video_css, 'Video is initialized')

    @wait_for_js
    def wait_for_video_player_render(self):
        """
        Wait until Video Player Rendered Completely.
        """
        self.wait_for_video_class()
        self._wait_for_element(CSS_CLASS_NAMES['video_init'], 'Video Player Initialized')
        self._wait_for_element(CSS_CLASS_NAMES['video_time'], 'Video Player Initialized')

        def _is_finished_loading():
            """
            Check if video loading completed
            :return: bool
            """
            return not self.q(css=CSS_CLASS_NAMES['video_spinner']).visible

        EmptyPromise(_is_finished_loading, 'Finished loading the video', timeout=200).fulfill()

        self.wait_for_ajax()

    def get_video_vertical_css(self, video_display_name=None):
        """
        Get CSS for a video vertical.
        :param video_display_name: strs
        """
        if video_display_name:
            video_display_names = self.q(css=CSS_CLASS_NAMES['video_display_name']).text
            assert video_display_name in video_display_names
            return '.vert.vert-{}'.format(video_display_names.index(video_display_name))
        else:
            return '.vert.vert-0'

    def is_video_rendered(self, mode, video_display_name=None):
        """
        Check that if video is rendered in `mode`.
        :param mode: Video mode, `html5` or `youtube`
        """
        html_tag = VIDEO_MODES[mode]
        css = '{0} {1} {2}'.format(self.get_video_vertical_css(video_display_name), CSS_CLASS_NAMES['video_container'],
                                   html_tag)

        def _is_element_present():
            """
            Check if a web element is present in DOM
            :return:
            """
            is_present = self.q(css=css).present
            return is_present, is_present

        return Promise(_is_element_present, 'Video Rendering Failed in {0} mode.'.format(mode)).fulfill()

    @property
    def is_autoplay_enabled(self, video_display_name=None):
        """
        Extract `data-autoplay` attribute to check video autoplay is enabled or disabled.
        """
        css = '{0} {1}'.format(self.get_video_vertical_css(video_display_name), CSS_CLASS_NAMES['video_container'])
        auto_play = self.q(css=css).attrs('data-autoplay')[0]

        if auto_play.lower() == 'false':
            return False

        return True

    @property
    def is_error_message_shown(self, video_display_name=None):
        """
        Checks if video player error message shown.
        :return: bool
        """
        css = '{0} {1}'.format(self.get_video_vertical_css(video_display_name), CSS_CLASS_NAMES['error_message'])
        return self.q(css=css).visible

    @property
    def error_message_text(self, video_display_name=None):
        """
        Extract video player error message text.
        :return: str
        """
        css = '{0} {1}'.format(self.get_video_vertical_css(video_display_name), CSS_CLASS_NAMES['error_message'])
        return self.q(css=css).text[0]

    def is_button_shown(self, button_id, video_display_name=None):
        """
        Check if a video button specified by `button_id` is visible
        :param button_id: button css selector
        :return: bool
        """
        css = '{0} {1}'.format(self.get_video_vertical_css(video_display_name), VIDEO_BUTTONS[button_id])
        return self.q(css=css).visible

    @wait_for_js
    def show_captions(self, video_display_name=None):
        """
        Show the video captions.
        """
        subtitle_css = '{0} {1}'.format(self.get_video_vertical_css(video_display_name),
                                        CSS_CLASS_NAMES['closed_captions'])

        def _is_subtitles_open():
            """
            Check if subtitles are opened
            :return: bool
            """
            is_open = not self.q(css=subtitle_css).present
            return is_open

        # Make sure that the CC button is there
        EmptyPromise(lambda: self.is_button_shown('CC', video_display_name),
                     "CC button is shown").fulfill()

        # Check if the captions are already open and click if not
        if _is_subtitles_open() is False:
            self.click_player_button('CC', video_display_name)

        # Verify that they are now open
        EmptyPromise(_is_subtitles_open,
                     "Subtitles are shown").fulfill()

    @property
    def captions_text(self, video_display_name=None):
        """
        Extract captions text.
        :return: str
        """
        # wait until captions rendered completely
        captions_rendered_css = '{0} {1}'.format(self.get_video_vertical_css(video_display_name),
                                                 CSS_CLASS_NAMES['captions_rendered'])
        self._wait_for_element(captions_rendered_css, 'Captions Rendered')

        captions_css = '{0} {1}'.format(self.get_video_vertical_css(video_display_name),
                                        CSS_CLASS_NAMES['captions_text'])
        subs = self.q(css=captions_css).html

        return ' '.join(subs)

    def set_speed(self, speed, video_display_name=None):
        """
        Change the video play speed.
        :param speed: speed value in str
        """
        current_video_vertical_css = self.get_video_vertical_css(video_display_name)

        speed_menu_js_code = "$('{0} .speeds').addClass('is-opened')".format(current_video_vertical_css)
        self.browser.execute_script(speed_menu_js_code)

        speed_css = '{0} li[data-speed="{1}"] a'.format(current_video_vertical_css, speed)
        self.q(css=speed_css).first.click()

    def get_speed(self, video_display_name=None):
        """
        Get current video speed value.
        :return: str
        """
        speed_css = '{0} .speeds .value'.format(self.get_video_vertical_css(video_display_name))
        return self.q(css=speed_css).text[0]

    def click_player_button(self, button, video_display_name=None):
        """
        Click on `button`.
        :param button: key in VIDEO_BUTTONS dictionary, its value will give us the css selector for `button`
        """
        video_vertical_css = self.get_video_vertical_css(video_display_name)
        button_css = '{0} {1}'.format(video_vertical_css, VIDEO_BUTTONS[button])
        self.q(css=button_css).first.click()

        if button == 'play':
            # wait for video buffering
            self._wait_for_video_play(video_vertical_css)

        self.wait_for_ajax()

    def _wait_for_video_play(self, video_vertical_css):
        """
        Wait until video starts playing
        :param video_vertical_css (str): css selector video vertical
        :return: BrokenPromise
        """
        css_playing = '{0} {1}'.format(video_vertical_css, CSS_CLASS_NAMES['video_container'])
        css_pause = '{0} {1}'.format(video_vertical_css, VIDEO_BUTTONS['pause'])

        def _check_promise():
            """
            Promise check
            :return: bool
            """
            return 'is-playing' in self.q(css=css_playing).attrs('class')[0] and self.q(css=css_pause).present

        EmptyPromise(_check_promise, 'Video is Playing', timeout=200).fulfill()

    def _get_element_dimensions(self, selector):
        """
        Gets the width and height of element specified by `selector`
        :param selector: str, css selector of a web element
        :return: dict
        """
        element = self.q(css=selector).results[0]
        return element.size

    def _get_dimensions(self, video_display_name=None):
        """
        Gets the video player dimensions
        :return: tuple
        """
        video_vertical_css = self.get_video_vertical_css(video_display_name)

        video = self._get_element_dimensions(
            '{0} .video-player iframe, {0} .video-player video'.format(video_vertical_css))
        wrapper = self._get_element_dimensions('{0} .tc-wrapper'.format(video_vertical_css))
        controls = self._get_element_dimensions('{0} .video-controls'.format(video_vertical_css))
        progress_slider = self._get_element_dimensions('{0} .video-controls > .slider'.format(video_vertical_css))

        expected = dict(wrapper)
        expected['height'] -= controls['height'] + 0.5 * progress_slider['height']

        return video, expected

    def is_aligned(self, is_transcript_visible, video_display_name=None):
        """
        Check if video is aligned properly.
        :param is_transcript_visible: bool
        :return: bool
        """
        # Width of the video container in css equal 75% of window if transcript enabled
        wrapper_width = 75 if is_transcript_visible else 100
        initial = self.browser.get_window_size()

        self.browser.set_window_size(300, 600)

        # Wait for browser to resize completely
        # Currently there is no other way to wait instead of explicit wait
        time.sleep(0.2)

        real, expected = self._get_dimensions(video_display_name)

        width = round(100 * real['width'] / expected['width']) == wrapper_width

        self.browser.set_window_size(600, 300)

        # Wait for browser to resize completely
        # Currently there is no other way to wait instead of explicit wait
        time.sleep(0.2)

        real, expected = self._get_dimensions(video_display_name)

        height = abs(expected['height'] - real['height']) <= 5

        # Restore initial window size
        self.browser.set_window_size(
            initial['width'], initial['height']
        )

        return all([width, height])

    def _get_transcript(self, url):
        """
        Sends a http get request.
        """
        kwargs = dict()

        session_id = [{i['name']: i['value']} for i in self.browser.get_cookies() if i['name'] == u'sessionid']
        if session_id:
            kwargs.update({
                'cookies': session_id[0]
            })

        response = requests.get(url, **kwargs)
        return response.status_code < 400, response.headers, response.content

    def downloaded_transcript_contains_text(self, transcript_format, text_to_search, video_display_name=None):
        """
        Download the transcript in format `transcript_format` and check that it contains the text `text_to_search`
        :param transcript_format: `srt` or `txt`
        :param text_to_search: str
        :return: bool
        """
        current_video_vertical_css = self.get_video_vertical_css(video_display_name)

        transcript_css = '{0} {1}'.format(current_video_vertical_css, VIDEO_MENUS['transcript-format'])

        # check if we have a transcript with correct format
        assert '.' + transcript_format in self.q(css=transcript_css).text[0]

        formats = {
            'srt': 'application/x-subrip',
            'txt': 'text/plain',
        }

        download_transcript_css = '{0} {1}'.format(current_video_vertical_css, VIDEO_BUTTONS['download_transcript'])
        url = self.q(css=download_transcript_css).attrs('href')[0]
        result, headers, content = self._get_transcript(url)

        assert result
        assert formats[transcript_format] in headers.get('content-type', '')
        assert text_to_search in content.decode('utf-8')

    def select_language(self, code, video_display_name=None):
        """
        Select captions for language `code`
        :param code: str, two character language code like `en`, `zh`
        :return: bool, True for Success, False for Failure or BrokenPromise
        """
        self.wait_for_ajax()

        current_video_vertical_css = self.get_video_vertical_css(video_display_name)

        # mouse over to CC button
        cc_button_css = '{0} {1}'.format(current_video_vertical_css, VIDEO_BUTTONS["CC"])
        element_to_hover_over = self.q(css=cc_button_css).results[0]
        hover = ActionChains(self.browser).move_to_element(element_to_hover_over)
        hover.perform()

        selector = VIDEO_MENUS["language"] + ' li[data-lang-code="{code}"]'.format(code=code)
        selector = '{0} {1}'.format(current_video_vertical_css, selector)
        self.q(css=selector).first.click()

        assert 'is-active' == self.q(css=selector).attrs('class')[0]

        css = '{0} {1}'.format(current_video_vertical_css, VIDEO_MENUS["language"] + ' li.is-active')
        assert len(self.q(css=css).results) == 1

        # Make sure that all ajax requests that affects the display of captions are finished.
        # For example, request to get new translation etc.
        self.wait_for_ajax()

        captions_css = '{0} {1}'.format(current_video_vertical_css, CSS_CLASS_NAMES['captions'])
        EmptyPromise(lambda: self.q(css=captions_css).visible, 'Subtitles Visible').fulfill()

        # wait until captions rendered completely
        captions_rendered_css = '{0} {1}'.format(current_video_vertical_css, CSS_CLASS_NAMES['captions_rendered'])
        self._wait_for_element(captions_rendered_css, 'Captions Rendered')

    def state(self, video_display_name=None):
        """
        Extract the current state(play, pause etc) of video
        :param video_display_name (str):
        :return: str
        """
        state_css = '{} {}'.format(self.get_video_vertical_css(video_display_name), CSS_CLASS_NAMES['video_container'])
        current_state = self.q(css=state_css).attrs('class')[0]

        if 'is-playing' in current_state:
            return 'playing'
        elif 'is-paused' in current_state:
            return 'pause'
        elif 'is-buffered' in current_state:
            return 'buffering'

    def is_menu_exist(self, menu_name, video_display_name=None):
        """
        Check if menu `menu_name` exists
        :param menu_name: menu name
        :return: bool
        """
        css = '{0} {1}'.format(self.get_video_vertical_css(video_display_name), VIDEO_MENUS[menu_name])
        return self.q(css=css).present

    def select_transcript_format(self, transcript_format, video_display_name=None):
        """
        Select transcript with format `transcript_format`
        :param transcript_format: `srt` or `txt`
        :return: bool
        """
        video_vertical_css = self.get_video_vertical_css(video_display_name)

        button_selector = '{} {}'.format(video_vertical_css, VIDEO_MENUS['transcript-format'])

        button = self.q(css=button_selector).results[0]

        height = button.location_once_scrolled_into_view['y']
        self.browser.execute_script("window.scrollTo(0, {});".format(height))

        hover = ActionChains(self.browser).move_to_element(button)
        hover.perform()

        assert '...' in self.q(css=button_selector).text[0]

        menu_selector = '{} {}'.format(video_vertical_css, VIDEO_MENUS['download_transcript'])
        menu_items = self.q(css=menu_selector + ' a').results
        for item in menu_items:
            if item.get_attribute('data-value') == transcript_format:
                item.click()
                self.wait_for_ajax()
                break

        self.browser.execute_script("window.scrollTo(0, 0);")

        assert self.q(css=menu_selector + ' .active a').attrs('data-value')[0] == transcript_format

        assert '.' + transcript_format in self.q(css=button_selector).text[0]
