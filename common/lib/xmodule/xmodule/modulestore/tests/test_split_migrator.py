"""
Tests for split_migrator

"""
import uuid
import random
import mock
from xmodule.modulestore.loc_mapper_store import LocMapperStore
from xmodule.modulestore.split_migrator import SplitMigrator
from xmodule.modulestore.mongo import draft
from xmodule.modulestore.tests import test_location_mapper
from xmodule.modulestore.tests.test_split_w_old_mongo import SplitWMongoCourseBoostrapper
from nose.tools import nottest


@nottest
class TestMigration(SplitWMongoCourseBoostrapper):
    """
    Test the split migrator
    """

    def setUp(self):
        super(TestMigration, self).setUp()
        # pylint: disable=W0142
        self.loc_mapper = LocMapperStore(test_location_mapper.TrivialCache(), **self.db_config)
        self.split_mongo.loc_mapper = self.loc_mapper
        self.migrator = SplitMigrator(self.split_mongo, self.old_mongo, self.draft_mongo, self.loc_mapper)

    def tearDown(self):
        dbref = self.loc_mapper.db
        dbref.drop_collection(self.loc_mapper.location_map)
        super(TestMigration, self).tearDown()

    def _create_course(self):
        """
        A course testing all of the conversion mechanisms:
        * some inheritable settings
        * sequences w/ draft and live intermixed children to ensure all get to the draft but
        only the live ones get to published. Some are only draft, some are both, some are only live.
        * about, static_tab, and conditional documents
        """
        super(TestMigration, self)._create_course(split=False)

        # chapters
        chapter1_name = uuid.uuid4().hex
        self._create_item('chapter', chapter1_name, {}, {'display_name': 'Chapter 1'}, 'course', 'runid', split=False)
        chap2_loc = self.old_course_key.make_usage_key('chapter', uuid.uuid4().hex)
        self._create_item(
            chap2_loc.category, chap2_loc.name, {}, {'display_name': 'Chapter 2'}, 'course', 'runid', split=False
        )
        # vertical in live only
        live_vert_name = uuid.uuid4().hex
        self._create_item(
            'vertical', live_vert_name, {}, {'display_name': 'Live vertical'}, 'chapter', chapter1_name,
            draft=False, split=False
        )
        self.create_random_units(False, self.old_course_key.make_usage_key('vertical', live_vert_name))
        # vertical in both live and draft
        both_vert_loc = self.old_course_key.make_usage_key('vertical', uuid.uuid4().hex)
        self._create_item(
            both_vert_loc.category, both_vert_loc.name, {}, {'display_name': 'Both vertical'}, 'chapter', chapter1_name,
            draft=False, split=False
        )
        self.create_random_units(False, both_vert_loc)
        draft_both = self.draft_mongo.get_item(both_vert_loc)
        draft_both.display_name = 'Both vertical renamed'
        self.draft_mongo.update_item(draft_both)
        self.create_random_units(True, both_vert_loc)
        # vertical in draft only (x2)
        draft_vert_loc = self.old_course_key.make_usage_key('vertical', uuid.uuid4().hex)
        self._create_item(
            draft_vert_loc.category, draft_vert_loc.name, {}, {'display_name': 'Draft vertical'}, 'chapter', chapter1_name,
            draft=True, split=False
        )
        self.create_random_units(True, draft_vert_loc)
        draft_vert_loc = self.old_course_key.make_usage_key('vertical', uuid.uuid4().hex)
        self._create_item(
            draft_vert_loc.category, draft_vert_loc.name, {}, {'display_name': 'Draft vertical2'}, 'chapter', chapter1_name,
            draft=True, split=False
        )
        self.create_random_units(True, draft_vert_loc)

        # and finally one in live only (so published has to skip 2)
        live_vert_loc = self.old_course_key.make_usage_key('vertical', uuid.uuid4().hex)
        self._create_item(
            live_vert_loc.category, live_vert_loc.name, {}, {'display_name': 'Live vertical end'}, 'chapter', chapter1_name,
            draft=False, split=False
        )
        self.create_random_units(True, draft_vert_loc)

        # now the other chapter w/ the conditional
        # create pointers to children (before the children exist)
        indirect1_loc = self.old_course_key.make_usage_key('discussion', uuid.uuid4().hex)
        indirect2_loc = self.old_course_key.make_usage_key('html', uuid.uuid4().hex)
        conditional_loc = self.old_course_key.make_usage_key('conditional', uuid.uuid4().hex)
        self._create_item(
            conditional_loc.category, conditional_loc.name,
            {
                'show_tag_list': [indirect1_loc, indirect2_loc],
                'sources_list': [live_vert_loc, ],
            },
            {
                'xml_attributes': {
                    'completed': True,
                },
            },
            chap2_loc.category, chap2_loc.name,
            draft=False, split=False
        )
        # create the children
        self._create_item(
            indirect1_loc.category, indirect1_loc.name, {'data': ""}, {'display_name': 'conditional show 1'},
            conditional_loc.category, conditional_loc.name,
            draft=False, split=False
        )
        self._create_item(
            indirect2_loc.category, indirect2_loc.name, {'data': ""}, {'display_name': 'conditional show 2'},
            conditional_loc.category, conditional_loc.name,
            draft=False, split=False
        )

        # add direct children
        self.create_random_units(False, conditional_loc)

        # and the ancillary docs (not children)
        self._create_item(
            'static_tab', uuid.uuid4().hex, {'data': ""}, {'display_name': 'Tab uno'},
            None, None, draft=False, split=False
        )
        self._create_item(
            'about', 'overview', {'data': "<p>test</p>"}, {},
            None, None, draft=False, split=False
        )
        self._create_item(
            'course_info', 'updates', {'data': "<ol><li><h2>Sep 22</h2><p>test</p></li></ol>"}, {},
            None, None, draft=False, split=False
        )

    def create_random_units(self, draft, parent_loc):
        """
        Create a random selection of units under the given parent w/ random names & attrs
        :param store: which store (e.g., direct/draft) to create them in
        :param parent: the parent to have point to them
        (only makes sense if store is 'direct' and this is 'draft' or vice versa)
        """
        for _ in range(random.randrange(6)):
            location = parent_loc.replace(
                category=random.choice(['html', 'video', 'problem', 'discussion']),
                name=uuid.uuid4().hex
            )
            metadata = {'display_name': str(uuid.uuid4()), 'graded': True}
            data = {}
            self._create_item(
                location.category, location.name, data, metadata, parent_loc.category, parent_loc.name,
                draft=draft, split=False
            )

    def compare_courses(self, presplit, published):
        # descend via children to do comparison
        old_root = presplit.get_course(self.old_course_key)
        new_root_locator = self.loc_mapper.translate_location_to_course_locator(
            old_root.id, published
        )
        new_root = self.split_mongo.get_course(new_root_locator)
        self.compare_dags(presplit, old_root, new_root, published)

        # grab the detached items to compare they should be in both published and draft
        for category in ['conditional', 'about', 'course_info', 'static_tab']:
            for conditional in presplit.get_items(self.old_course_key, category=category):
                locator = self.loc_mapper.translate_location(
                    conditional.location,
                    published,
                    add_entry_if_missing=False
                )
                self.compare_dags(presplit, conditional, self.split_mongo.get_item(locator), published)

    def compare_dags(self, presplit, presplit_dag_root, split_dag_root, published):
        # check that locations match
        self.assertEqual(
            presplit_dag_root.location,
            self.loc_mapper.translate_locator_to_location(split_dag_root.location).replace(revision=None)
        )
        # compare all fields but children
        for name in presplit_dag_root.fields.iterkeys():
            if name != 'children':
                self.assertEqual(
                    getattr(presplit_dag_root, name),
                    getattr(split_dag_root, name),
                    "{}/{}: {} != {}".format(
                        split_dag_root.location, name, getattr(presplit_dag_root, name), getattr(split_dag_root, name)
                    )
                )
        # test split get_item using old Location: old draft store didn't set revision for things above vertical
        # but split does distinguish these; so, set revision if not published
        if not published:
            location = draft.as_draft(presplit_dag_root.location)
        else:
            location = presplit_dag_root.location
        refetched = self.split_mongo.get_item(location)
        self.assertEqual(
            refetched.location, split_dag_root.location,
            "Fetch from split via old Location {} not same as new {}".format(
                refetched.location, split_dag_root.location
            )
        )
        # compare children
        if presplit_dag_root.has_children:
            self.assertEqual(
                # need get_children to filter out drafts
                len(presplit_dag_root.get_children()), len(split_dag_root.children),
                "{0.category} '{0.display_name}': children  {1} != {2}".format(
                    presplit_dag_root, presplit_dag_root.children, split_dag_root.children
                )
            )
            for pre_child, split_child in zip(presplit_dag_root.get_children(), split_dag_root.get_children()):
                self.compare_dags(presplit, pre_child, split_child, published)

    def test_migrator(self):
        user = mock.Mock(id=1)
        self.migrator.migrate_mongo_course(self.old_course_key, user)
        # now compare the migrated to the original course
        self.compare_courses(self.old_mongo, True)
        self.compare_courses(self.draft_mongo, False)
