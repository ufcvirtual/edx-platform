"""
Settings for the LMS that runs alongside the CMS on AWS
"""

# We intentionally define lots of variables that aren't used, and
# want to import all variables from base settings files
# pylint: disable=W0401, W0614

from ..aws import *

with open(ENV_ROOT / "cms.auth.json") as auth_file:
    CMS_AUTH_TOKENS = json.load(auth_file)

MODULESTORE = CMS_AUTH_TOKENS['MODULESTORE']

HOSTNAME_MODULESTORE_DEFAULT_MAPPINGS = ENVS_TOKENS.get('HOSTNAME_MODULESTORE_DEFAULT_MAPPINGS',{})
