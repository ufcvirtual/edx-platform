(function (define) {
'use strict';
define(
'video/00_i18n.js',
[],
function() {
    /**
     * i18n module.
     * @exports video/00_i18n.js
     * @return {object}
     */

    return {
        // Translators: "points" is the student's achieved score, and "total_points" is the maximum number of points achievable.
        '(%(points)s / %(total_points)s points)': gettext('(%(points)s / %(total_points)s points)'),
        'Feedback on your work from the grader:': gettext('Feedback on your work from the grader:'),
        'This video was successfully scored!': gettext('This video was successfully scored!'),
        GRADER_ERROR: gettext('Error happens. Sorry for the inconvenience, restart the page and try again.')
    };
});
}(RequireJS.define));

