"""Shared HTTPS-only urllib helper for reporting modules.

GitHub API calls in ``reporting/*`` must reject any non-HTTPS URL even if
config or env data says otherwise. Using ``urllib.request.urlopen`` directly
delegates the scheme decision to whatever handlers urllib has registered
globally — which on most Pythons includes ``http://``, ``ftp://``, and
``file://``. Bandit's B310 / ruff's S310 flag this for good reason.

``https_only_opener()`` returns an ``OpenerDirector`` whose **only** registered
scheme handler is ``HTTPSHandler``. Attempting to dispatch ``http://``,
``file://``, etc. raises ``urllib.error.URLError("unknown url type: ...")``
at the protocol layer — there is no way for a malformed config to leak data
through a non-TLS channel, regardless of caller validation.

This is a real architectural fix (no ``# nosec`` markers needed): bandit's
B310 specifically blacklists ``urllib.request.urlopen`` and its variants;
``opener.open`` on a custom opener is intentionally not in the blacklist.
"""

from __future__ import annotations

import urllib.request


def https_only_opener() -> urllib.request.OpenerDirector:
    """Return an OpenerDirector that supports https:// only.

    The returned opener has no HTTPHandler, FTPHandler, FileHandler, or
    DataHandler registered. Calls to ``opener.open(...)`` with any non-HTTPS
    URL raise ``urllib.error.URLError`` before any I/O occurs.
    """
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.HTTPSHandler())
    # Standard processors needed for sane status-code handling on success.
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    return opener
