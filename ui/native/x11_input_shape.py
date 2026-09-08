"""Input-region policy for the temporary xcb/XWayland runtime.

MagicScribe currently forces Qt's xcb backend on a Wayland KDE session while
native parity is being validated.  Toggling QWindow flags on an already visible
QQuickWindow proved unstable on the target desktop, so xcb uses the XShape
input region just like the proven legacy overlay.  This module is native policy
only; drawing state and rendering remain outside it.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging

logger = logging.getLogger(__name__)

_SHAPE_INPUT = 2
_SHAPE_SET = 0
_x11_libs: tuple[object, object] | None | bool = None


def _load_x11_libs() -> tuple[object, object] | None:
    """Load X11/Xext once and declare the ctypes signatures we use."""
    global _x11_libs
    if _x11_libs is False:
        return None
    if isinstance(_x11_libs, tuple):
        return _x11_libs

    x11_path = ctypes.util.find_library("X11")
    xext_path = ctypes.util.find_library("Xext")
    if not x11_path or not xext_path:
        _x11_libs = False
        return None

    try:
        x11 = ctypes.cdll.LoadLibrary(x11_path)
        xext = ctypes.cdll.LoadLibrary(xext_path)

        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XCreateRegion.restype = ctypes.c_void_p
        x11.XCreateRegion.argtypes = []
        x11.XDestroyRegion.argtypes = [ctypes.c_void_p]
        x11.XDestroyRegion.restype = None
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XFlush.restype = None
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = None

        xext.XShapeCombineRegion.restype = None
        xext.XShapeCombineRegion.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        xext.XShapeCombineMask.restype = None
        xext.XShapeCombineMask.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_int,
        ]
    except (OSError, AttributeError) as exc:
        logger.warning("X11/Xext non disponibile: %s", exc)
        _x11_libs = False
        return None

    _x11_libs = (x11, xext)
    return _x11_libs


def set_x11_click_through(window_id: int, enabled: bool) -> bool:
    """Set or clear the X11 Shape input region for one native window.

    Returns True only when the request was actually applied.  An empty input
    region makes the window click-through; resetting the mask restores normal
    pointer input without changing/recreating Qt window flags.
    """
    if window_id <= 0:
        return False

    libs = _load_x11_libs()
    if libs is None:
        return False
    x11, xext = libs

    display = x11.XOpenDisplay(None)
    if not display:
        logger.warning("Impossibile aprire il display X11 per l'input shape")
        return False

    try:
        xid = ctypes.c_ulong(window_id)
        if enabled:
            region = x11.XCreateRegion()
            if not region:
                return False
            try:
                xext.XShapeCombineRegion(
                    display,
                    xid,
                    _SHAPE_INPUT,
                    0,
                    0,
                    region,
                    _SHAPE_SET,
                )
            finally:
                x11.XDestroyRegion(region)
        else:
            xext.XShapeCombineMask(
                display,
                xid,
                _SHAPE_INPUT,
                0,
                0,
                ctypes.c_ulong(0),
                _SHAPE_SET,
            )
        x11.XFlush(display)
    except Exception:
        logger.exception("Applicazione X11 input shape fallita")
        return False
    finally:
        x11.XCloseDisplay(display)

    logger.debug("X11 input shape: click_through=%s, win=%s", enabled, window_id)
    return True
