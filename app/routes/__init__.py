from app.routes.auth import router as auth_router
from app.routes.dev import router as dev_router
from app.routes.pages import router as pages_router
from app.routes.contacts_api import router as contacts_api_router
from app.routes.properties_api import router as properties_api_router
from app.routes.deals_api import router as deals_api_router
from app.routes.tasks_api import router as tasks_api_router
from app.routes.i18n_api import router as i18n_api_router
from app.routes.calendar_api import router as calendar_api_router
from app.routes.documents_api import router as documents_api_router
from app.routes.reports_api import router as reports_api_router
from app.routes.chat_api import router as chat_api_router
from app.routes.settings_api import router as settings_api_router

__all__ = [
    "auth_router", "dev_router", "pages_router",
    "contacts_api_router", "properties_api_router",
    "deals_api_router", "tasks_api_router", "i18n_api_router",
    "calendar_api_router", "documents_api_router", "reports_api_router",
    "chat_api_router", "settings_api_router",
]
