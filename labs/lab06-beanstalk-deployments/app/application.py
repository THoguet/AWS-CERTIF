"""lab06: a tiny WSGI application for Elastic Beanstalk.

The Python platform runs it with Gunicorn and looks for a callable named `application` in
application.py (the default WSGIPath). No dependencies are needed.
"""

import json
import os
import socket

VERSION = "1"
BROKEN = False   # set to True to ship a release that fails its health checks


def application(environ, start_response):
    if BROKEN:
        start_response("500 Internal Server Error", [("Content-Type", "application/json")])
        return [json.dumps({"error": f"release {VERSION} is broken"}).encode()]
    body = {
        "version": VERSION,
        "color": os.environ.get("COLOR", "unset"),   # an environment property (.ebextensions or eb setenv)
        "instance": socket.gethostname(),           # which EC2 instance answered
        "path": environ.get("PATH_INFO", "/"),
    }
    start_response("200 OK", [("Content-Type", "application/json")])
    return [json.dumps(body).encode()]
