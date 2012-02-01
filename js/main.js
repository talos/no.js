/*jslint browser: true*/
/*globals require */

require([
    'text!../templates/list.mustache',
    'text!../templates/game.mustache',
    'text!../templates/you.mustache',
    'text!../templates/updates.mustache',
    'text!../templates/chat.mustache',
    'lib/jquery',
    'lib/requirejs.mustache',
    'lib/json2'
], function (list, game, you, updates, chat, $, mustache, json) {
    "use strict";

    // argh: http://stackoverflow.com/questions/2037295/getjson-back-button-showing-json-return-data-not-the-page
    // also: http://code.google.com/p/chromium/issues/detail?id=68096
    $.ajaxSetup({ cache: false });

    var $app = $('#app'),
        $chat = $app.find('#chat'),
        lastPoll = null,

        /**
          *  This binds selectors/data to templates.
          **/
        templates = {
            list: list,
            game: game,
            you: you,
            updates: updates
        },

        /**
         * Update the page for given id.  This polls, immediately
         * making another request for the next ID upon completion.
         *
         * @param id The ID to request.
         */
        update = function (id) {

            // Make sure we're not double-polling.
            if (lastPoll !== null) {
                if (!lastPoll.isResolved() && !lastPoll.isRejected()) {
                    lastPoll.abort();
                }
            }

            var data = typeof id === 'undefined' ? {} : { id : id };

            lastPoll = $.getJSON(window.location.pathname, data)
                .done(function (resp, status, doc) {
                    if (doc.responseText) {
                        var context = json.parse(doc.responseText);
                        $.each(templates, function (id, template) {
                            $app.find('#' + id).html(mustache.render(template, context));
                        });

                        // This is hacky, but have to make sure that
                        // chat is only updated if it is empty.
                        if ($chat.children().length === 0) {
                            $chat.html(mustache.render(chat, context));
                        }
                        id = context.id;
                    }
                    setTimeout(function () {
                        update(id);
                    }, 100);
                }).fail(function (resp) {
                    //console.log(resp);
                });
        };

    update();

    // absorb POST form hits
    $(document).on('submit', 'form', function () {
        var $form = $(this);

        if ($form.attr('method') === 'post') {
            $.ajax({ url: $form.attr('action'),
                     dataType: 'json',
                     type: 'POST',
                     data: $form.serialize()
                   })
                .done(function () {
                    // clear text inputs
                    $form.find('input[type="text"]').val('');
                    // force a full refresh
                    update();
                });
            return false;
        } else {
            return true;
        }
    });
});
