"""
Classes used to model the roles used in the courseware. Each role is responsible for checking membership,
adding users, removing users, and listing members
"""

from abc import ABCMeta, abstractmethod

from django.contrib.auth.models import User
from student.models import CourseAccessRole


class CourseIdRequired(Exception):
    """
    Raised when a course_id is required to determine permissions
    """
    pass


class AccessRole(object):
    """
    Object representing a role with particular access to a resource
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def has_user(self, user):  # pylint: disable=unused-argument
        """
        Return whether the supplied django user has access to this role.
        """
        return False

    @abstractmethod
    def add_users(self, *users):
        """
        Add the role to the supplied django users.
        """
        pass

    @abstractmethod
    def remove_users(self, *users):
        """
        Remove the role from the supplied django users.
        """
        pass

    @abstractmethod
    def users_with_role(self):
        """
        Return a django QuerySet for all of the users with this role
        """
        return User.objects.none()


class GlobalStaff(AccessRole):
    """
    The global staff role
    """
    def has_user(self, user):
        return user.is_staff

    def add_users(self, *users):
        for user in users:
            if (user.is_authenticated() and user.is_active):
                user.is_staff = True
                user.save()

    def remove_users(self, *users):
        for user in users:
            # don't check is_authenticated nor is_active on purpose
            user.is_staff = False
            user.save()

    def users_with_role(self):
        raise Exception("This operation is un-indexed, and shouldn't be used")


class GroupBasedRole(AccessRole):
    """
    A role based on having a role independent of org or course.
    """
    def __init__(self, role_name, org=None, course_key=None):
        """
        Create a GroupBasedRole from a group names
        """
        self.org = org
        self.course_key = course_key
        self._role_name = role_name

    def has_user(self, user):
        """
        Return whether the supplied django user has access to this role independent of org and course.
        """
        if not (user.is_authenticated() and user.is_active):
            return False

        # pylint: disable=protected-access
        if not hasattr(user, '_roles'):
            user._roles = list(
                CourseAccessRole.objects.filter(user=user).all()
            )

        role = CourseAccessRole(user=user, role=self._role_name, course_id=self.course_key, org=self.org)
        return role in user._roles

    def add_users(self, *users):
        """
        Add the supplied django users to this role.
        """
        # silently ignores anonymous and inactive users so that any that are
        # legit get updated.
        for user in users:
            if user.is_authenticated and user.is_active and not self.has_user(user):
                entry = CourseAccessRole(user=user, role=self._role_name, course_id=self.course_key, org=self.org)
                entry.save()
                if hasattr(user, '_roles'):
                    del user._roles

    def remove_users(self, *users):
        """
        Remove the supplied django users from this role.
        """
        if self.course_key:
            entries = CourseAccessRole.objects.filter(
                user__in=users, role=self._role_name, org=self.org, course_id=self.course_key
            )
        else:
            entries = CourseAccessRole.objects.filter(
                user__in=users, role=self._role_name, org=self.org
            )
        entries.delete()
        for user in users:
            if hasattr(user, '_roles'):
                del user._roles

    def users_with_role(self):
        """
        Return a django QuerySet for all of the users with this role
        """
        if self.course_key:
            entries = User.objects.filter(
                courseaccessrole__role=self._role_name,
                courseaccessrole__org=self.org,
                courseaccessrole__course_id=self.course_key
            )
        else:
            entries = User.objects.filter(
                courseaccessrole__role=self._role_name,
                courseaccessrole__org=self.org
            )
        return entries


class CourseRole(GroupBasedRole):
    """
    A named role in a particular course
    """
    def __init__(self, role, course_key):
        """
        Args:
            course_key (CourseKey)
        """
        super(CourseRole, self).__init__(role, course_key.org, course_key)

    @classmethod
    def course_group_already_exists(self, course_key):
        return CourseAccessRole.objects.filter(org=course_key.org, course_id=course_key).exists()


class OrgRole(GroupBasedRole):
    """
    A named role in a particular org independent of course
    """
    def __init__(self, role, org):
        super(OrgRole, self).__init__(role, org)


class CourseStaffRole(CourseRole):
    """A Staff member of a course"""
    ROLE = 'staff'

    def __init__(self, *args, **kwargs):
        super(CourseStaffRole, self).__init__(self.ROLE, *args, **kwargs)


class CourseInstructorRole(CourseRole):
    """A course Instructor"""
    ROLE = 'instructor'

    def __init__(self, *args, **kwargs):
        super(CourseInstructorRole, self).__init__(self.ROLE, *args, **kwargs)


class CourseBetaTesterRole(CourseRole):
    """A course Beta Tester"""
    ROLE = 'beta_testers'

    def __init__(self, *args, **kwargs):
        super(CourseBetaTesterRole, self).__init__(self.ROLE, *args, **kwargs)


class OrgStaffRole(OrgRole):
    """An organization staff member"""
    def __init__(self, *args, **kwargs):
        super(OrgStaffRole, self).__init__('staff', *args, **kwargs)


class OrgInstructorRole(OrgRole):
    """An organization instructor"""
    def __init__(self, *args, **kwargs):
        super(OrgInstructorRole, self).__init__('instructor', *args, **kwargs)


class CourseCreatorRole(GroupBasedRole):
    """
    This is the group of people who have permission to create new courses (we may want to eventually
    make this an org based role).
    """
    ROLE = "course_creator_group"

    def __init__(self, *args, **kwargs):
        super(CourseCreatorRole, self).__init__(self.ROLE, *args, **kwargs)


class UserBasedRole(object):
    """
    Backward mapping: given a user, manipulate the courses and roles
    """
    def __init__(self, user, role):
        """
        Create a UserBasedRole accessor: for a given user and role (e.g., "instructor")
        """
        self.user = user
        self.role = role

    def has_course(self, course_key):
        """
        Return whether the role's user has the configured role access to the passed course
        """
        if not (self.user.is_authenticated() and self.user.is_active):
            return False

        # pylint: disable=protected-access
        if not hasattr(self.user, '_roles'):
            self.user._roles = list(
                CourseAccessRole.objects.filter(user=self.user).all()
            )

        role = CourseAccessRole(user=self.user, role=self.role, course_id=course_key, org=course_key.org)
        return role in self.user._roles

    def add_course(self, *course_keys):
        """
        Grant this object's user the object's role for the supplied courses
        """
        if self.user.is_authenticated and self.user.is_active:
            for course_key in course_keys:
                entry = CourseAccessRole(user=self.user, role=self.role, course_id=course_key, org=course_key.org)
                entry.save()
            if hasattr(self.user, '_roles'):
                del user._roles
        else:
            raise ValueError("user is not active. Cannot grant access to courses")

    def remove_courses(self, *course_keys):
        """
        Remove the supplied courses from this user's configured role.
        """
        entries = CourseAccessRole.objects.filter(user=self.user, role=self.role, course_id__in=course_keys)
        entries.delete()
        if hasattr(self.user, '_roles'):
            del self.user._roles

    def courses_with_role(self):
        """
        Return a django QuerySet for all of the courses with this user x role. You can access
        any of these properties on each result record:
        * user (will be self.user--thus uninteresting)
        * org
        * course_id
        * role (will be self.role--thus uninteresting)
        """
        return CourseAccessRole.objects.filter(role=self.role, user=self.user)
