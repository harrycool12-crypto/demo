import os
import jinja2
from starlette.templating import Jinja2Templates as _Jinja2Templates

_TMPL_DIR = os.path.join(os.path.dirname(__file__), "templates")
_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_TMPL_DIR),
    cache_size=0,
    autoescape=jinja2.select_autoescape(["html"]),
)
_base = _Jinja2Templates(env=_env)


class _CompatTemplates:
    """Wraps Starlette 1.3 Jinja2Templates with the old positional API:
       TemplateResponse(name, {"request": req, ...})
    """
    def TemplateResponse(self, name: str, context: dict, **kwargs):
        ctx = dict(context)
        request = ctx.pop("request")
        return _base.TemplateResponse(request, name, ctx, **kwargs)

    def __getattr__(self, item):
        return getattr(_base, item)


templates = _CompatTemplates()
