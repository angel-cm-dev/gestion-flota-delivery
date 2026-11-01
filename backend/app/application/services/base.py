from collections.abc import Callable
from datetime import date

from sqlalchemy.orm import Session

from app.core.clock import today_lima
from app.core.config import Settings


class Service:
    """Base de los casos de uso.

    Recibe la sesión (unidad de trabajo), la configuración y un reloj
    inyectable: las pruebas pasan un ``today`` fijo para que las reglas de
    vencimiento sean deterministas.
    """

    def __init__(self, session: Session, settings: Settings, today: Callable[[], date] = today_lima) -> None:
        self.session = session
        self.settings = settings
        self.today = today

    def commit(self) -> None:
        self.session.commit()
