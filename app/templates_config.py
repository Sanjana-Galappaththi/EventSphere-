from starlette.templating import Jinja2Templates
from typing import Any

class CompatibleJinja2Templates(Jinja2Templates):
    """
    Compatible Jinja2Templates that seamlessly supports both:
    1. Modern Starlette: TemplateResponse(request=request, name=name, context=context)
    2. Legacy Starlette: TemplateResponse(name, context={"request": request, ...})
    """
    def TemplateResponse(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.get("context", {})
            request = context.get("request") if isinstance(context, dict) else kwargs.get("request")
            return super().TemplateResponse(request=request, name=name, context=context)
        return super().TemplateResponse(*args, **kwargs)

templates = CompatibleJinja2Templates(directory="app/templates")
