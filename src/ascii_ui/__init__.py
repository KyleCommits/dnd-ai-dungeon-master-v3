# src/ascii_ui - ASCII terminal presentation + command routing
from .frames import box, clamp_width, panel, wrap_text


async def handle_terminal_command(*args, **kwargs):
    from .commands import handle_terminal_command as _handle

    return await _handle(*args, **kwargs)


# Re-export dataclass for type/import convenience without pulling heavy deps at import.
def __getattr__(name: str):
    if name == "TerminalCommandResult":
        from .commands import TerminalCommandResult

        return TerminalCommandResult
    raise AttributeError(name)


__all__ = [
    "TerminalCommandResult",
    "handle_terminal_command",
    "box",
    "clamp_width",
    "panel",
    "wrap_text",
]
