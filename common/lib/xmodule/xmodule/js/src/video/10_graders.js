(function (define) {
'use strict';
define(
'video/10_graders.js',
['video/00_abstract_grader.js'],
function (AbstractGrader) {
    /**
     * GraderChooser module.
     * @exports video/10_graders.js
     * @constructor
     * @param {object} state The object containing the state of the video
     * player.
     * @return {jquery Promise}
     */
    var GraderChooser = function (state, i18n) {
        if (!(this instanceof GraderChooser)) {
            return new GraderChooser(state, i18n);
        }

        debugger;

        var graderName = state.config.graderName,
            _this = this;

        this.graderInstances = [];

        if (state.config.hasScore) {
            $.each(state.config.graders, function (graderName, graderConfig) {
                var graderInstance;

                debugger;

                if (GraderChooser[graderName]) {
                    graderInstance = new GraderChooser[graderName](state, i18n, graderConfig);

                    _this.graderInstances.push(graderInstance);
                }
            });

            // if (GraderChooser[graderName]) {
            //     return new GraderChooser[graderName](state, i18n);
            // }
        }

        return $.Deferred().resolve().promise();
    };

    // Write graders below this line

    GraderChooser.GradeOnEnd = AbstractGrader.extend({
        getGrader: function (element, state) {
            var dfd = $.Deferred();
            element.on('ended', dfd.resolve);

            return dfd.promise();
        }
    });

    return GraderChooser;
});

}(window.RequireJS.define));
