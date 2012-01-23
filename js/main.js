/*jslint browser: true*/
/*globals require */

require([
    'opengold/request',
    'text!templates/join.mustache',
    'text!templates/start.mustache',
    'text!templates/in_progress.mustache',
    'text!templates/finished.mustache',
    'lib/jquery',
    'lib/mustache'
], function (request, join, start, in_progress, finished, $, mustache) {
    "use strict";
    var $el = $('#opengold'),
        game_name = window.location.pathname.slice(1);

    // absorb form hits
    $('form').submit(function () {
        console.log(this);
        return false;
    });

    request.status(game_name, function (status) {
        var template;
        switch (status.type) {
        case 'start':
            template = start;
            break;
        case 'join':
            template = join;
            break;
        case 'in_progress':
            template = in_progress;
            break;
        case 'finished':
            template = finished;
            break;
        }
        $el.html(mustache.render(template, status));

        console.log(this);
        request.poll(game_name, this);
    });
});
