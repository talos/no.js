from brubeck.request_handling import WebMessageHandler

import pystache # TODO this should be moved to the env_loader area

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
        from pystache import Loader
        loader = Loader()
        loader.template_path = template_dir or '.'
        return loader

    return loader

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
        template = mustache_env.load_template(template_file)
        body = pystache.render(template, context or {})
        self.set_body(body, status_code=_status_code)
        return self.render()

    def render_error(self, error_code):
        """Receives error calls and sends them through a templated renderer
        call.
        """
        return self.render_template('errors', _status_code=error_code,
                                    **{'error_code': error_code})
