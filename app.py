"""Main Flask WSGI application hosting Product Price Service hooks."""

from views import create_app

app, _, __ = create_app(testing=False)

# TODO: consider port configuration, etc.
if __name__ == '__main__':
    app.run(debug=True)
