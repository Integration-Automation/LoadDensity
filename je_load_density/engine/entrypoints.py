"""Scheduler selection without importing or patching the unselected engine."""

import asyncio
from typing import Any, Dict, Optional


def start_test(
    user_detail_dict: Dict[str, Any],
    user_count: int = 50,
    spawn_rate: int = 10,
    test_time: Optional[int] = 60,
    web_ui_dict: Optional[Dict[str, Any]] = None,
    runner_mode: str = "local",
    load_shape: Optional[str] = None,
    shape_config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Select Locust (default) or local native asyncio HTTP with the legacy signature."""
    engine = kwargs.pop("engine", "locust")
    arguments = (
        user_detail_dict,
        user_count,
        spawn_rate,
        test_time,
        web_ui_dict,
        runner_mode,
        load_shape,
        shape_config,
    )
    if engine == "locust":
        from je_load_density.wrapper.start_wrapper.locust_start import start_test as start_locust

        return start_locust(*arguments, **kwargs)
    if engine != "asyncio":
        raise ValueError(f"Unsupported engine: {engine!r}")
    return _start_native(arguments, kwargs)


def _start_native(arguments: tuple, options: dict) -> dict:
    detail, users, rate, duration, web_ui, mode, shape, shape_config = arguments
    if detail.get("user", "fast_http_user") not in {"http_user", "fast_http_user", "async_http_user"}:
        raise ValueError("Native asyncio currently supports HTTP users only")
    if set(detail) - {"user", "host", "base_url"}:
        raise ValueError("Unsupported native user configuration")
    if web_ui:
        raise ValueError("Native asyncio does not provide the Locust web UI")
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Use await run_async_load() inside an active asyncio event loop")
    from je_load_density.engine.asyncio_engine import run_async_load

    tasks = options.pop("tasks", None)
    options.setdefault("base_url", detail.get("host", detail.get("base_url", "")))
    native = asyncio.run(
        run_async_load(
            tasks,
            users,
            duration,
            spawn_rate=rate,
            runner_mode=mode,
            load_shape=shape,
            shape_config=shape_config,
            **options,
        )
    )
    return {
        "user_detail": detail,
        "user_count": users,
        "spawn_rate": rate,
        "test_time": duration,
        "web_ui": web_ui,
        "runner_mode": mode,
        "engine": "asyncio",
        "state": native["state"],
        "summary": native["summary"],
    }
