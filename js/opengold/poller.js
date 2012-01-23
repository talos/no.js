/*globals define */

define([
    'lib/jquery',
    'lib/json2'
], function ($, json) {
    "use strict";

    var json_request = function (method, path, handler) {
        return $.ajax(path, { type: method })
            .done(function (resp, status, doc) {
                handler(json.parse(doc.responseText));
            }).fail(function (resp) {
                console.log(resp.statusText); // TODO
            });
    },

        status = function (game_name, handler) {
            return json_request('get', game_name + '/status', handler);
        },

        poll = function (game_name, handler) {
            return json_request('post', game_name + '/poll', handler);
                // .always(function () {
                //     setTimeout(function () {
                //         poll(game_name, handler); // is this safe for the stack?
                //     }, 1000); // safety latch
                // });
        };

    return { status: status, poll: poll };
});