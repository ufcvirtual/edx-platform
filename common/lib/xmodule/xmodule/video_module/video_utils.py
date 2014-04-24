"""
Module containts utils specific for video_module but not for transcripts.
"""


def create_youtube_string(module):
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
    return ','.join([
        ':'.join(pair)
        for pair
        in zip(youtube_speeds, youtube_ids)
        if pair[1]
    ])


def grade_url(self):
    """
    Return grade url for 3rd party handler.

    Should deprecated after https://github.com/edx/edx-platform/pull/2685 gets merged.
    """
    scheme = 'http' if 'sandbox' in self.system.hostname or self.system.debug else 'https'
    uri = '{scheme}://{host}{path}'.format(
    scheme=scheme,
        host=self.system.hostname,
        path=self.runtime.handler_url(self, 'grade_handler', thirdparty=True).rstrip('/?')
        )
    return uri
