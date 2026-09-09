from contextvars import ContextVar
from uuid import UUID, uuid4

current_request_id: ContextVar[UUID | None] = ContextVar(
    "current_request_id",
    default=None,
)


def set_current_request_id(request_id):
    current_request_id.set(request_id)
    return request_id


def get_current_request_id():
    value = current_request_id.get()
    if value is None:
        return uuid4()
    return value
