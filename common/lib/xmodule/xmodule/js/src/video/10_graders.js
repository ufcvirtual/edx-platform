(function (define) {
'use strict';
define(
'video/10_graders.js',
['video/00_abstract_grader.js'],
function (AbstractGrader) {
    /**
     * GraderCollection module.
     * @exports video/10_graders.js
     * @constructor
     * @param {object} state The object containing the state of the video
     * player.
     * @return {jquery Promise}
     */
    var GraderCollection = function (state, i18n) {
        var _this;

        if (!(this instanceof GraderCollection)) {
            return new GraderCollection(state, i18n);
        }

        debugger;

        this.graderInstances = [];
        this.graderMap = {
            'scored_on_end': 'GradeOnEnd',
            'scored_on_percent': 'GradeOnPercent'
        };

        if (state.config.hasScore) {
            _this = this;

            $.each(state.config.graders, function (backendPropertyName, graderConfig) {
                var graderName = _this.graderMap[backendPropertyName],
                    graderInstance;

                debugger;

                if (GraderCollection[graderName]) {
                    graderInstance = new GraderCollection[graderName](state, i18n, graderConfig);

                    _this.graderInstances.push(graderInstance);
                }
            });
        }

        return $.Deferred().resolve().promise();
    };

    // Write graders below this line

    GraderCollection.GradeOnEnd = AbstractGrader.extend({
        getGrader: function (element, state) {
            var dfd = $.Deferred();
            element.on('ended', dfd.resolve);

            return dfd.promise();
        },

        backendPropertyName: 'scored_on_end'
    });

    GraderCollection.GradeOnPercent = AbstractGrader.extend({
        getGrader: function (element, state) {
            var dfd = $.Deferred();

            // TODO: Implement success scenario.
            // element.on('ended', dfd.resolve);

            return dfd.promise();
        },

        backendPropertyName: 'scored_on_percent'
    });

    return GraderCollection;
});

}(window.RequireJS.define));
