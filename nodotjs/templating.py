from brubeck.request_handling import WebMessageHandler

###
### Mustache
###

def load_mustache_env(template_dir, *args, **kwargs):
    """
    Returns a function that loads a mustache template environment. Uses a
    closure to provide a namespace around module loading without loading
    anything until the caller is ready.
    """
    def loader():
        return MustacheEnvironment(template_dir)

    return loader


class MustacheEnvironment(object):
    """
    An environment to render mustache templates.
    """
    def __init__(self, template_dirs):
        import pystache

        self.pystache = pystache
        self.template_dirs = template_dirs

    def render(self, template_file, context):
        view = self.pystache.View(context=context)
        view.template_name = template_file
        view.template_path = self.template_dirs
        return view.render()


class MustacheRendering(WebMessageHandler):
    """
    MustacheRendering is a mixin for for loading a Mustache rendering
    environment.

    Render success is transmitted via http 200. Rendering failures result in
    http 500 errors.
    """
    def render_template(self, template_file,
                        _status_code=WebMessageHandler._SUCCESS_CODE,
                        **context):
        """
        Renders payload as a mustache template
        """
        mustache_env = self.application.template_env
        body = mustache_env.render(template_file, context or {})

        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors', _status_code=error_code,
                                    **{'error_code': error_code})
