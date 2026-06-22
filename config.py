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
    """Wraps Starlette 1.3 Jinja2Templates.
    Auto-injects current_user from session cookie so every template has it.
    """
    def TemplateResponse(self, name: str, context: dict, **kwargs):
        import auth as _auth
        ctx = dict(context)
        request = ctx.pop("request")
        if "current_user" not in ctx:
            token = request.cookies.get("session_token", "")
            ctx["current_user"] = _auth.get_session_user(token) or "Admin"
        return _base.TemplateResponse(request, name, ctx, **kwargs)

    def __getattr__(self, item):
        return getattr(_base, item)


templates = _CompatTemplates()
