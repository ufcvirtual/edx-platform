(function (define) {
'use strict';
define(
'video/00_abstract_grader.js',
[],
function() {
    /**
     * AbstractGrader module.
     * @exports video/00_abstract_grader.js
     * @constructor
     * @param {object} state The object containing the state of the video
     * player.
     * @return {jquery Promise}
     */
    var AbstractGrader = function () { };

    AbstractGrader.extend = function (protoProps) {
        var Parent = this,
            Child = function () {
                if ($.isFunction(this['initialize'])) {
                    return this['initialize'].apply(this, arguments);
                }
            };

        // inherit
        var F = function () {};
        F.prototype = Parent.prototype;
        Child.prototype = new F();
        Child.constructor = Parent;
        Child.__super__ = Parent.prototype;

        if (protoProps) {
            $.extend(Child.prototype, protoProps);
        }

        return Child;
    };

    AbstractGrader.prototype = {
        /** Initializes the module. */
        initialize: function (state, i18n) {
            this.state = state;
            this.i18n = i18n;
            this.el = this.state.el;
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
                this.grader = this.getGrader(this.el, this.state);
                this.grader.done(this.sendGrade.bind(this));
            }

            return $.Deferred().resolve().promise();
        },

        /**
         * Factory method that returns instance of needed Grader.
         * @return {jquery Promise}
         * @example:
         *   var dfd = $.Deferred();
         *   this.el.on('play', dfd.resolve);
         *   return dfd.promise();
         */
        getGrader: function (element, state) {
            throw new Error('Please implement logic of the `getGrader` method.');
        },

        /**
         * Sends results of grading to the server.
         * @return {jquery Promise}
         */
        sendGrade: function () {
            return $.ajaxWithPrefix({
                url: this.url,
                type: 'POST',
                notifyOnError: false,
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

                if (type === 'error') {
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
                this.el.addClass('is-scored');
                this.updateStatusText(
                    this.i18n['This video was successfully scored!']
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
            var msg = this.i18n['GRADER_ERROR'];

            this.updateStatusText(msg, 'error');
            this.el.addClass('is-error');
        }
    };

    return AbstractGrader;
});
}(RequireJS.define));

