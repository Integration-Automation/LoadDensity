"""
Interactive LoadDensity REPL — ``loaddensity shell``.

Boots a Python ``code.InteractiveConsole`` with the public LoadDensity
surface (start_test, register_variable, etc.) pre-imported. Designed
for quick exploration without writing a project.
"""

import code
from typing import Optional


_BANNER = (
    "LoadDensity REPL — public API pre-imported as `ld`.\n"
    "Examples:\n"
    "  >>> ld.start_test(user_detail_dict={'user':'fast_http_user'},\n"
    "  ...               user_count=10, spawn_rate=2, test_time=10,\n"
    "  ...               tasks=[{'method':'get','request_url':'https://httpbin.org/get'}])\n"
    "  >>> print(ld.build_summary())\n"
    "Use Ctrl-D to exit."
)


def start_repl(banner: Optional[str] = None) -> None:
    """Drop the user into an interactive console with LoadDensity loaded."""
    import je_load_density as ld

    namespace = {"ld": ld}
    console = code.InteractiveConsole(locals=namespace)
    console.interact(banner=banner or _BANNER, exitmsg="")
