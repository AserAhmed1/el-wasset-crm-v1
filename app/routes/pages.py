from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def get_context(request: Request):
    lang = "ar"
    qlang = request.query_params.get("lang")
    if qlang in ("en", "ar"):
        lang = qlang
    elif request.cookies.get("lang") in ("en", "ar"):
        lang = request.cookies.get("lang")
    return {
        "request": request,
        "lang": lang,
        "user_name": "",
        "user_initials": "",
    }


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", get_context(request))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", get_context(request))


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", get_context(request))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", get_context(request))


@router.get("/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request):
    return templates.TemplateResponse("contacts.html", get_context(request))


@router.get("/properties", response_class=HTMLResponse)
async def properties_page(request: Request):
    return templates.TemplateResponse("properties.html", get_context(request))


@router.get("/deals", response_class=HTMLResponse)
async def deals_page(request: Request):
    return templates.TemplateResponse("deals.html", get_context(request))


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    return templates.TemplateResponse("tasks.html", get_context(request))


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request):
    return templates.TemplateResponse("calendar.html", get_context(request))


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    return templates.TemplateResponse("documents.html", get_context(request))


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", get_context(request))


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", get_context(request))


@router.get("/dev", response_class=HTMLResponse)
async def dev_page(request: Request):
    return templates.TemplateResponse("dev.html", get_context(request))


@router.get("/design", response_class=HTMLResponse)
async def design_page(request: Request):
    return templates.TemplateResponse("design.html", get_context(request))
