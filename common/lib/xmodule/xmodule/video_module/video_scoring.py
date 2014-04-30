"""
Contani methods for scoring video.
"""
import json


class VideoScoring(object):
    """
    Contain method for scoring video
    """

    def max_score(self):
        return self.weight if self.has_score else None

    def update_score(self, score):
        """
        Save grade to database.
        """
        anon_user_id  = self.runtime.anonymous_student_id
        assert anon_user_id is not None

        if callable(self.system.get_real_user):  # We are in LMS not in Studio, in Studio it is None.
            real_user = self.system.get_real_user(anon_user_id)
        else:
            raise NotImplementedError

        assert real_user is not None  # We can't save to database, as we do not have real user id.

        self.system.publish(
            self,
            'grade',
            {
                'value': score,
                'max_value': self.max_score(),
                'user_id': real_user.id,
            }
        )

        self.module_score = score
        log.debug("[Video]: Grade is saved.")

    def graders(self):
        """
        Select active graders from possible graders.

        Fields that start with 'scored' are counted as possible graders.

        If grader was added or removed, or it's value was changed,
        clear self.cumulative_score and clear score in database.

        Returns:
            dumped dict of { grader field name: (score_status, grader value)} format,
            where score_status is bool, and True if condition for that grader was
            satisfied.
        """

        if self.module_score and self.module_score == self.max_score():  # module have been scored
            return json.dumps({})

        active_graders = {
            name: getattr(self, name)
            for name in self.fields.keys()
            if name.startswith('scored') and getattr(self, name)
        }

        graders_updated = sorted(self.cumulative_score) != sorted(active_graders)
        graders_values_changed = False

        if not graders_updated:
            for grader_name, cumulative_score_value in self.cumulative_score.items():
                score_status, grader_value = cumulative_score_value
                if grader_value != active_graders[grader_name]:
                    graders_values_changed = True
                    break

        if graders_updated or graders_values_changed:
            self.cumulative_score = {
                grader_name: (False, grader_value)
                for grader_name, grader_value in active_graders.items()
            }

        return json.dumps(self.cumulative_score)
