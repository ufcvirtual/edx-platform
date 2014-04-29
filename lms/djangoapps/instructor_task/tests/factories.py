import json

import factory
from factory.django import DjangoModelFactory
from student.tests.factories import UserFactory as StudentUserFactory
from instructor_task.models import InstructorTask
from celery.states import PENDING
from xmodule.modulestore.locations import SlashSeparatedCourseKey


class InstructorTaskFactory(DjangoModelFactory):
    FACTORY_FOR = InstructorTask

    task_type = 'rescore_problem'
    course_id = SlashSeparatedCourseKey("MITx", "999", "Robot_Super_Course")
    task_input = json.dumps({})
    task_key = None
    task_id = None
    task_state = PENDING
    task_output = None
    requester = factory.SubFactory(StudentUserFactory)
