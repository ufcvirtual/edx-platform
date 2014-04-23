from django.conf import settings
from django.test.utils import override_settings
from xmodule.modulestore.django import LmsMetadataService
from xmodule.modulestore.tests.django_utils import studio_store_config, ModuleStoreTestCase

TEST_MODULESTORE = studio_store_config(settings.TEST_ROOT / "data")

@override_settings(MODULESTORE=TEST_MODULESTORE)
class TestPreviewLmsMetadataService(ModuleStoreTestCase):

    def test_preview_enabled(self):
        service = LmsMetadataService()
        self.assertTrue(service.is_preview_enabled())

class TestProdLmsMetadataService(ModuleStoreTestCase):

    def test_preview_not_enabled(self):
        service = LmsMetadataService()
        self.assertFalse(service.is_preview_enabled())