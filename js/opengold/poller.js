/*globals require */

require([
    'lib/jquery',
    'lib/json2'
], function ($, json) {
    "use strict";

    var poll = function (game_name, handler) {
        $.get(game_name + '/poll')
            .done(function (resp, status, doc) {
                handler(json.parse(doc.responseText));
            }).fail(function (resp) {
                console.log(resp); // TODO
            }).always(function () {
                poll(game_name); // is this safe for the stack?
            });
    };

    return { poll: poll };
});