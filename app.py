[2026-03-02 11:55:49,425] ERROR in app: Exception on / [GET]
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1511, in wsgi_app
    response = self.full_dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 919, in full_dispatch_request
    rv = self.handle_user_exception(e)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 917, in full_dispatch_request
    rv = self.dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 902, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "/opt/render/project/src/app.py", line 201, in index
    return render_template(
        "index.html",
    ...<9 lines>...
        }
    )
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/templating.py", line 151, in render_template
    return _render(app, template, context)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/templating.py", line 132, in _render
    rv = template.render(context)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/jinja2/environment.py", line 1295, in render
    self.environment.handle_exception()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/jinja2/environment.py", line 942, in handle_exception
    raise rewrite_traceback_stack(source=source)
  File "/opt/render/project/src/templates/index.html", line 139, in top-level template code
    href="{{ url_for('view_resort', resort_id=resort.id) }}">
    ^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1121, in url_for
    return self.handle_url_build_error(error, endpoint, values)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1110, in url_for
    rv = url_adapter.build(  # type: ignore[union-attr]
        endpoint,
    ...<3 lines>...
        force_external=_external,
    )
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/werkzeug/routing/map.py", line 901, in build
    raise BuildError(endpoint, values, method, self)
werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'view_resort' with values ['resort_id']. Did you mean 'new_resort' instead?
127.0.0.1 - - [02/Mar/2026:11:55:49 +0000] "GET / HTTP/1.1" 500 265 "-" "Go-http-client/2.0"
[2026-03-02 11:56:42,518] ERROR in app: Exception on / [GET]
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1511, in wsgi_app
    response = self.full_dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 919, in full_dispatch_request
    rv = self.handle_user_exception(e)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 917, in full_dispatch_request
    rv = self.dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 902, in dispatch_request
127.0.0.1 - - [02/Mar/2026:11:56:42 +0000] "GET / HTTP/1.1" 500 265 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "/opt/render/project/src/app.py", line 201, in index
    return render_template(
        "index.html",
    ...<9 lines>...
        }
    )
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/templating.py", line 151, in render_template
    return _render(app, template, context)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/templating.py", line 132, in _render
    rv = template.render(context)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/jinja2/environment.py", line 1295, in render
    self.environment.handle_exception()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/jinja2/environment.py", line 942, in handle_exception
    raise rewrite_traceback_stack(source=source)
  File "/opt/render/project/src/templates/index.html", line 139, in top-level template code
    href="{{ url_for('view_resort', resort_id=resort.id) }}">
    ^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1121, in url_for
    return self.handle_url_build_error(error, endpoint, values)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1110, in url_for
    rv = url_adapter.build(  # type: ignore[union-attr]
        endpoint,
    ...<3 lines>...
        force_external=_external,
    )
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/werkzeug/routing/map.py", line 901, in build
    raise BuildError(endpoint, values, method, self)
werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'view_resort' with values ['resort_id']. Did you mean 'new_resort' instead?
127.0.0.1 - - [02/Mar/2026:11:56:42 +0000] "GET /favicon.ico HTTP/1.1" 404 207 "https://resort-accessibili.onrender.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
[2026-03-02 11:56:46 +0000] [56] [INFO] Handling signal: term
[2026-03-02 11:56:46 +0000] [59] [INFO] Worker exiting (pid: 59)
[2026-03-02 11:56:46 +0000] [56] [INFO] Shutting down: Master
[2026-03-02 11:56:48,411] ERROR in app: Exception on / [GET]
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1511, in wsgi_app
    response = self.full_dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 919, in full_dispatch_request
    rv = self.handle_user_exception(e)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 917, in full_dispatch_request
    rv = self.dispatch_request()
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 902, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "/opt/render/project/src/app.py", line 201, in index
    return render_template(
        "index.html",
    ...<9 lines>...
        }
    )
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/templating.py", line 151, in render_template
    return _render(app, template, context)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/templating.py", line 132, in _render
    rv = template.render(context)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/jinja2/environment.py", line 1295, in render
    self.environment.handle_exception()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/jinja2/environment.py", line 942, in handle_exception
    raise rewrite_traceback_stack(source=source)
  File "/opt/render/project/src/templates/index.html", line 139, in top-level template code
    href="{{ url_for('view_resort', resort_id=resort.id) }}">
    ^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1121, in url_for
    return self.handle_url_build_error(error, endpoint, values)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/flask/app.py", line 1110, in url_for
    rv = url_adapter.build(  # type: ignore[union-attr]
        endpoint,
    ...<3 lines>...
        force_external=_external,
    )
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/werkzeug/routing/map.py", line 901, in build
    raise BuildError(endpoint, values, method, self)
werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'view_resort' with values ['resort_id']. Did you mean 'new_resort' instead?
127.0.0.1 - - [02/Mar/2026:11:56:48 +0000] "GET / HTTP/1.1" 500 265 "-" "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
127.0.0.1 - - [02/Mar/2026:11:56:48 +0000] "GET /favicon.ico HTTP/1.1" 404 207 "https://resort-accessibili.onrender.com/" "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
