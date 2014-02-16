![No (dot) JS](http://www.nodotjs.com/assets/img/logo.gif)

# No (dot) JS Chat 

### Real-time chat, nary a line of client side code. 

##### IE4-tested, mother approved.

[Read](http://blog.accursedware.com/html-only-live-chat:-No.JS/) about it.

See it [in action](http://www.nodotjs.com/).

### Use it

The only external dependency is redis.  Make sure you have it running locally
on port 6379.  You should be able to modify the database using `config.ini`
(which will be generated automatically when you first run the server.)

All other dependencies are in `requirements.txt`.

    pip install -r requirements.txt
    python nodotjs/server.py staging

You can also change which port the server runs on in `config.ini`.
