=============
RTV Changelog
=============

.. _1.4.1: http://github.com/michael-lazar/rtv/releases/tag/v1.4.1
.. _1.4: http://github.com/michael-lazar/rtv/releases/tag/v1.4
.. _1.3: http://github.com/michael-lazar/rtv/releases/tag/v1.3
.. _1.2.2: http://github.com/michael-lazar/rtv/releases/tag/v1.2.2
.. _1.2.1: http://github.com/michael-lazar/rtv/releases/tag/v1.2.1
.. _1.2: http://github.com/michael-lazar/rtv/releases/tag/v1.2

-------------------
1.4.1_ (2015-07-11)
-------------------
Features

* Added the ability to check for unread messages with the `i` key.
* Upped required PRAW version to 3

Bugfixes

* Fixed crash caused by downvoting.
* Missing flairs now display properly.
* Fixed ResourceWarning on Python 3.2+.

-----------------
1.4_ (2015-05-16)
-----------------
Features

* Unicode support has been vastly improved and is now turned on by default. Ascii only mode can be toggled with the `--ascii` command line flag.
* Added pageup and pagedown with the `m` and `n` keys.
* Support for terminal based webbrowsers such as links and w3m.
* Browsing history is now persistant and stored in `$XDG_CACHE_HOME`.

Bugfixes

* Several improvements for handling unicode.
* Fixed crash caused by resizing the window and exiting a submission.

-----------------
1.3_ (2015-04-22)
-----------------
Features

* Added edit `e` and delete `d` for comments and submissions.
* Added *nsfw* tags.

Bugfixes

* Upvote/downvote icon now displays in the submission selfpost.
* Loading large *MoreComment* blocks no longer hangs the program.
* Improved logging and error handling with praw interactions.

-------------------
1.2.2_ (2015-04-07)
-------------------
Bugfixes

* Fixed default subreddit not being set.

Documentation

* Added changelog and contributor links to the README.

-------------------
1.2.1_ (2015-04-06)
-------------------
Bugfixes

* Fixed crashing on invalid subreddit names

-----------------
1.2_ (2015-04-06)
-----------------
Features

* Added user login / logout with the `u` key.
* Added subreddit searching with the `f` key.
* Added submission posting with the `p` key.
* Added viewing of user submissions with `/r/me`.
* Program title now displays in the terminal window.
* Gold symbols now display on guilded comments and posts.
* Moved default config location to XDG_CONFIG_HOME.

Bugfixes

* Improved error handling for submission / comment posts.
* Fixed handling of unicode flairs.
* Improved displaying of the help message and selfposts on small terminal windows.
* The author's name now correctly highlights in submissions
* Corrected user agent formatting.
* Various minor bugfixes.

------------------
1.1.1 (2015-03-30)
------------------
* Post comments using your text editor.
