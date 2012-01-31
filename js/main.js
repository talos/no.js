/*jslint browser: true*/
/*globals require */

require([
    'text!../templates/game.mustache',
    'lib/jquery',
    'lib/requirejs.mustache',
    'lib/json2'
], function (game, $, mustache, json) {
    "use strict";
    var $game = $('#game'),

        /**
         * Update the page for given id.  This polls, immediately
         * making another request for the next ID upon completion.
         *
         * @param id The ID to request.
         */
        update = function (id) {
            var data = id ? { id : id } : {};

            $.getJSON(window.location.pathname, data)
                .done(function (resp, status, doc) {
                    var context = json.parse(doc.responseText);
                    $game.html(mustache.render(game, context));
                    update(context.id);
                }).fail(function (resp) {
                    console.log(resp);
                });
        };

    update(0);

    // absorb form hits
    $('form').submit(function () {
        console.log(this);
        return false;
    });
});
