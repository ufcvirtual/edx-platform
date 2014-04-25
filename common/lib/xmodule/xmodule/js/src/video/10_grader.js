(function (define) {
'use strict';
define(
'video/10_grader.js',
[],
function () {
    /**
     * Grader module.
     * @exports video/10_grader.js
     * @constructor
     * @param {object} state The object containing the state of the video
     * player.
     * @return {jquery Promise}
     */
    var Grader = function (state) {
        if (!(this instanceof Grader)) {
            return new Grader(state);
        }

        var i18n = {
            // Translators: "points" is the student's achieved score, and "total_points" is the maximum number of points achievable.
            '(%(points)s / %(total_points)s points)': gettext('(%(points)s / %(total_points)s points)'),
            'Feedback on your work from the grader:': gettext('Feedback on your work from the grader:'),
            'This problem was successfully scored!': gettext('This problem was successfully scored!'),
            'Error happens. Sorry for the inconvenience, restart your page and try again.': gettext('Error happens. Sorry for the inconvenience, restart your page and try again.')
        };

        this.state = state;
        this.state.videoGrader = this;

        if (this.state.config.hasScore) {
            this.initialize(i18n);
        }

        return $.Deferred().resolve().promise();
    };

    Grader.prototype = {
        /** Initializes the module. */
        initialize: function (i18n) {
            this.el = this.state.el;
            this.i18n = i18n;
            this.maxScore = this.state.config.maxScore;
            this.score = this.state.config.score;
            this.url = this.state.config.gradeUrl;
            this.progressElement = this.state.progressElement;
            this.statusElement = this.state.statusElement;
            this.statusMsgElement = this.statusElement
                                        .find('.problem-feedback-message');

            if (this.score && isFinite(this.score)) {
                this.setScore(this.score);
            } else {
                this.grader = this.getGrader();
                this.grader.done(this.sendGrade.bind(this));
            }
        },

        /**
         * Factory method that returns instance of needed Grader.
         * @return {jquery Promise}
         * @example:
         *   var dfd = $.Deferred();
         *   this.el.on('play', dfd.resolve);
         *   return dfd.promise();
         */
        getGrader: function () {
            console.log('Please implement logic of `getGrader` method.');
        },

        /**
         * Sends results of grading to the server.
         * @return {jquery Promise}
         */
        sendGrade: function () {
            return $.ajax({
                url: this.url,
                type: 'POST',
                success: this.onSuccess.bind(this),
                error: this.onError.bind(this)
            });
        },

        /**
         * Updates scores on the front-end.
         * @param {number|string} points Score achieved by the student.
         * @param {number|string} totalPoints Maximum number of points
         * achievable.
         */
        updateScores: function (points, totalPoints) {
            var msg = interpolate(
                    this.i18n['(%(points)s / %(total_points)s points)'],
                    {
                        'points': points,
                        'total_points': totalPoints
                    }, true
                );

            this.progressElement.text(msg);
        },

        /**
         * Creates status element and inserts it to the DOM.
         * @param {string} message Status message.
         */
        createStatusElement: function (message) {
            this.statusElement = $([
                '<div class="problem-feedback">',
                    '<h4 class="problem-feedback-label">',
                        this.i18n['Feedback on your work from the grader:'],
                    '</h4>',
                    '<div class="problem-feedback-message">',
                        message ? message : '',
                    '</div>',
                '</div>'
            ].join(''));

            this.statusMsgElement = this.statusElement
                                        .find('.problem-feedback-message');
            this.el.after(this.statusElement);
        },

        /**
         * Updates status message by the text passed as argument.
         * @param {string} text Text of status message.
         * @param {string} type The type of the message: error or success.
         */
        updateStatusText: function (text, type) {
            if (text) {
                if (this.statusElement.length) {
                    this.statusMsgElement.text(text);
                } else {
                    this.createStatusElement(text);
                }

                if (type === "error") {
                    this.statusElement.addClass('is-error');
                } else {
                    this.statusElement.removeClass('is-error');
                }
            }
        },

        /**
         * Updates current score for the module.
         * @param {number|string} points Score achieved by the student.
         */
        setScore: function (points) {
            this.score = points;
            this.state.storage.setItem('score', this.score, true);
            this.updateScores(this.score, this.maxScore);
        },

        /**
         * Handles success response from the server after sending grade results.
         * @param {object} response Data returned from the server.
         * @param {string} textStatus String describing the status.
         * @param {jquery XHR} jqXHR
         */
        onSuccess: function (response) {
            if (isFinite(response)) {
                this.setScore(response);
                this.el.addClass('is-graded');
                this.updateStatusText(
                    this.i18n['This problem was successfully scored!']
                );
            }
        },

        /**
         * Handles failed response from the server after sending grade results.
         * @param {jquery XHR} jqXHR
         * @param {string} textStatus String describing the type of error that
         * occurred and an optional exception object, if one occurred.
         * @param {string} errorThrown Textual portion of the HTTP status.
         */
        onError: function () {
            var msg = this.i18n['Error happens. Sorry for the inconvenience,' +
                ' restart your page and try again.'];

            this.updateStatusText(msg, 'error');
        }
    };

    return Grader;
});

}(RequireJS.define));
