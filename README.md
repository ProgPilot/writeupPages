# writeupPages

A Flask app written to host CTF writeups.

### Features
* Set per-CTF release times
* Fast
* Supports a variety of writeup formats including PDF, HTML and YouTube

### Why you shouldn't use this
This was created for ProgPilot and it may be difficult to change and update for your own use. Some, but not all of the
relevant configuration is stored in `settings.json`. Things like the content on the homepage are not dynamically
generated, so you will have to edit the template files yourself.

You might well be able to find something else that's more flexible than this, or you might be able to make something
that fits your specific requirements better than this does.

If you do decide to use this, feel free to report any bugs or ask for help. Setup should be simple, and you can proxy it
through the webserver of your choosing, for example with `mod_wsgi` for Apache.

### Demo instance

https://www.progpilot.com/writeups/

### Could this be improved?
Yes.

### Will it be improved?
Probably. Eventually.