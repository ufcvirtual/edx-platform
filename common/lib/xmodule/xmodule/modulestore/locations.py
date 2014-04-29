""" Contains Locations ___ """

import logging
import re

from opaque_keys import InvalidKeyError, OpaqueKey

from xmodule.modulestore.keys import CourseKey, UsageKey, DefinitionKey, AssetKey
import json

log = logging.getLogger(__name__)

URL_RE = re.compile("""
    (?P<tag>[^:]+)://?
    (?P<org>[^/]+)/
    (?P<course>[^/]+)/
    (?P<category>[^/]+)/
    (?P<name>[^@]+)
    (@(?P<revision>[^/]+))?
    """, re.VERBOSE)

# TODO (cpennington): We should decide whether we want to expand the
# list of valid characters in a location
INVALID_CHARS = re.compile(r"[^\w.%-]", re.UNICODE)
# Names are allowed to have colons.
INVALID_CHARS_NAME = re.compile(r"[^\w.:%-]", re.UNICODE)

# html ids can contain word chars and dashes
INVALID_HTML_CHARS = re.compile(r"[^\w-]", re.UNICODE)


class SlashSeparatedCourseKey(CourseKey):
    """Course key for old style org/course/run course identifiers"""

    CANONICAL_NAMESPACE = 'slashes'
    KEY_FIELDS = ('org', 'course', 'run')
    __slots__ = KEY_FIELDS

    @classmethod
    def _from_string(cls, serialized):
        serialized = serialized.replace("+", "/")
        if serialized.count('/') != 2:
            raise InvalidKeyError(cls, serialized)

        # Turns encoded slashes into actual slashes
        return cls(*serialized.split('/'))

    def _to_string(self):
        # Turns slashes into pluses
        return self.to_deprecated_string().replace("/", "+")

    @property
    def offering(self):
        return '/'.join([self.course, self.run])

    def make_asset_key(self, asset_type, path):
        return AssetLocation(self.org, self.course, self.run, asset_type, path, None)

    def make_usage_key(self, block_type, name):
        return Location(self.org, self.course, self.run, block_type, name, None)

    def to_deprecated_string(self):
        return '/'.join([self.org, self.course, self.run])

    @classmethod
    def from_deprecated_string(cls, serialized):
        return cls._from_string(serialized)

    def make_usage_key_from_deprecated_string(self, location_url):
        """
        Temporary mechanism for creating a UsageKey given a CourseKey and a serialized Location. NOTE:
        this prejudicially takes the tag, org, and course from the url not self.

        Also, it tries to interpret the string as a new format url if the old i4x format parse fails.

        It also checks whether for some reason the url is already a UsageKey and returns it w/o further
        ado.

        Raises:
            InvalidKeyError: if the url does not parse
        """
        if isinstance(location_url, UsageKey):
            return location_url
        match = URL_RE.match(location_url)
        if match is None:
            raise InvalidKeyError(Location, location_url)
        groups = match.groupdict()
        if 'tag' in groups:
            del groups['tag']
        return Location(run=self.run, **groups)


class LocationBase(object):
    """
    Encodes a location.

    Locations representations of URLs of the
    form {tag}://{org}/{course}/{category}/{name}[@{revision}], situated in the course
    {org}/{course}/{run}.
    """
    KEY_FIELDS = ('org', 'course', 'run', 'category', 'name', 'revision')

    @classmethod
    def _check_location_part(cls, val, regexp):
        """
        Check that `regexp` doesn't match inside `val`. If it does, raise an exception

        Args:
            val (string): The value to check
            regexp (re.RegexObject): The regular expression specifying invalid characters

        Raises:
            InvalidKeyError: Raised if any invalid character is found in `val`
        """
        if val is None:
            return

        if not isinstance(val, basestring):
            raise InvalidKeyError(cls, "{!r} is not a string".format(val))

        if regexp.search(val) is not None:
            raise InvalidKeyError(cls, "Invalid characters in {!r}.".format(val))

    @classmethod
    def _clean(cls, value, invalid):
        """
        invalid should be a compiled regexp of chars to replace with '_'
        """
        return re.sub('_+', '_', invalid.sub('_', value))

    @classmethod
    def clean(cls, value):
        """
        Return value, made into a form legal for locations
        """
        return cls._clean(value, INVALID_CHARS)

    @classmethod
    def clean_keeping_underscores(cls, value):
        """
        Return value, replacing INVALID_CHARS, but not collapsing multiple '_' chars.
        This for cleaning asset names, as the YouTube ID's may have underscores in them, and we need the
        transcript asset name to match. In the future we may want to change the behavior of _clean.
        """
        return INVALID_CHARS.sub('_', value)

    @classmethod
    def clean_for_url_name(cls, value):
        """
        Convert value into a format valid for location names (allows colons).
        """
        return cls._clean(value, INVALID_CHARS_NAME)

    @classmethod
    def clean_for_html(cls, value):
        """
        Convert a string into a form that's safe for use in html ids, classes, urls, etc.
        Replaces all INVALID_HTML_CHARS with '_', collapses multiple '_' chars
        """
        return cls._clean(value, INVALID_HTML_CHARS)

    def __init__(self, org, course, run, category, name, revision=None):
        """
        Create a new Location that is a clone of the specifed one.

        Components must be composed of alphanumeric characters, or the
        characters '_', '-', and '.'.  The name component is additionally allowed to have ':',
        which is interpreted specially for xml storage.

        Components may be set to None, which may be interpreted in some contexts
        to mean wildcard selection.
        """

        for part in (org, course, run, category, revision):
            self._check_location_part(part, INVALID_CHARS)
        self._check_location_part(name, INVALID_CHARS_NAME)

        super(LocationBase, self).__init__(org, course, run, category, name, revision)

    @property
    def tag(self):
        return self.DEPRECATED_TAG

    @property
    def definition_key(self):
        # Locations are both UsageKeys and DefinitionKeys
        return self

    def url(self):
        """
        Return a string containing the URL for this location
        """
        return self.to_deprecated_string()

    @classmethod
    def from_deprecated_string(cls, serialized):
        match = URL_RE.match(serialized)
        if match is None:
            raise InvalidKeyError(Location, serialized)
        groups = match.groupdict()
        if 'tag' in groups:
            del groups['tag']
        return Location(run=None, **groups)

    def to_deprecated_string(self):
        url = u"{0.DEPRECATED_TAG}://{0.org}/{0.course}/{0.category}/{0.name}".format(self)
        if self.revision:
            url += u"@{rev}".format(rev=self.revision)  # pylint: disable=E1101
        return url

    def _to_string(self):
        output = u"/".join(
            unicode(val)
            for val in (self.org, self.course, self.run, self.category, self.name)
        )
        if self.revision:
            output += u'@{}'.format(self.revision)
        return output.replace("/", "+")

    @classmethod
    def _from_string(cls, serialized):
        serialized = serialized.replace("+", "/")
        pattern = """
            (?P<org>[^/]+)/
            (?P<course>[^/]+)/
            (?P<run>[^/]+)/
            (?P<category>[^/]+)/
            (?P<name>[^@/]+)
            (@(?P<revision>[^/]+))?
        """

        match = re.match(pattern, serialized, re.VERBOSE)
        if not match:
            raise InvalidKeyError(cls, serialized)

        return cls(**match.groupdict())

    def html_id(self):
        """
        Return a string with a version of the location that is safe for use in
        html id attributes
        """
        id_fields = [self.DEPRECATED_TAG, self.org, self.course, self.category, self.name, self.revision]
        id_string = u"-".join([v for v in id_fields if v is not None])
        return Location.clean_for_html(id_string)

    @property
    def course_key(self):
        return SlashSeparatedCourseKey(self.org, self.course, self.run)


class Location(LocationBase, UsageKey, DefinitionKey):

    CANONICAL_NAMESPACE = 'location'
    DEPRECATED_TAG = 'i4x'
    __slots__ = LocationBase.KEY_FIELDS

    def map_into_course(self, course_key):
        return Location(course_key.org, course_key.course, course_key.run, self.category, self.name, self.revision)


class AssetLocation(LocationBase, AssetKey):
    CANONICAL_NAMESPACE = 'asset-location'
    DEPRECATED_TAG = 'c4x'
    __slots__ = LocationBase.KEY_FIELDS

    def __init__(self, org, course, run, category, name, revision=None):
        super(AssetLocation, self).__init__(org, course, run, category, name, revision)

    @property
    def path(self):
        return self.name

    def to_deprecated_string(self):
        url = u"/{0.DEPRECATED_TAG}/{0.org}/{0.course}/{0.category}/{0.name}".format(self)
        return url

    def map_into_course(self, course_key):
        return AssetLocation(course_key.org, course_key.course, course_key.run, self.category, self.name, self.revision)


class i4xEncoder(json.JSONEncoder):
    """
    If provided as the cls to json.dumps, will serialize and Locations as i4x strings and other
    keys using the unicode strings.
    """
    def default(self, key):
        if isinstance(key, OpaqueKey):
            if isinstance(key, (LocationBase, SlashSeparatedCourseKey)):
                return key.to_deprecated_string()
            else:
                return unicode(key)
        super(i4xEncoder, self).default(key)
