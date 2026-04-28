from typing import Any, Dict, Optional

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.wrapper.create_locust_env.create_locust_env import prepare_env
from je_load_density.wrapper.user_template.fast_http_user_template import (
    FastHttpUserWrapper,
    set_wrapper_fasthttp_user,
)
from je_load_density.wrapper.user_template.grpc_user_template import (
    GrpcUserWrapper,
    set_wrapper_grpc_user,
)
from je_load_density.wrapper.user_template.http_user_template import (
    HttpUserWrapper,
    set_wrapper_http_user,
)
from je_load_density.wrapper.user_template.mqtt_user_template import (
    MqttUserWrapper,
    set_wrapper_mqtt_user,
)
from je_load_density.wrapper.user_template.socket_user_template import (
    SocketUserWrapper,
    set_wrapper_socket_user,
)
from je_load_density.wrapper.user_template.websocket_user_template import (
    WebSocketUserWrapper,
    set_wrapper_websocket_user,
)


_USER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "fast_http_user": {"actually_user": FastHttpUserWrapper, "init": set_wrapper_fasthttp_user},
    "http_user": {"actually_user": HttpUserWrapper, "init": set_wrapper_http_user},
    "websocket_user": {"actually_user": WebSocketUserWrapper, "init": set_wrapper_websocket_user},
    "grpc_user": {"actually_user": GrpcUserWrapper, "init": set_wrapper_grpc_user},
    "mqtt_user": {"actually_user": MqttUserWrapper, "init": set_wrapper_mqtt_user},
    "socket_user": {"actually_user": SocketUserWrapper, "init": set_wrapper_socket_user},
}


def start_test(
    user_detail_dict: Dict[str, Any],
    user_count: int = 50,
    spawn_rate: int = 10,
    test_time: Optional[int] = 60,
    web_ui_dict: Optional[Dict[str, Any]] = None,
    runner_mode: str = "local",
    master_bind_host: str = "*",
    master_bind_port: int = 5557,
    master_host: str = "127.0.0.1",
    master_port: int = 5557,
    expected_workers: int = 0,
    **kwargs,
) -> Dict[str, Any]:
    """
    啟動壓力測試。Start load test.

    runner_mode: local | master | worker
    """
    load_density_logger.info(
        f"start_test, user_detail_dict={user_detail_dict}, user_count={user_count}, "
        f"spawn_rate={spawn_rate}, test_time={test_time}, web_ui_dict={web_ui_dict}, "
        f"runner_mode={runner_mode}, params={kwargs}"
    )

    user_type = user_detail_dict.get("user", "fast_http_user")
    user = _USER_REGISTRY.get(user_type)
    if user is None:
        raise ValueError(f"Unsupported user type: {user_type}")

    actually_user = user["actually_user"]
    init_function = user["init"]

    init_function(user_detail_dict, **kwargs)

    prepare_env(
        user_class=actually_user,
        user_count=user_count,
        spawn_rate=spawn_rate,
        test_time=test_time,
        web_ui_dict=web_ui_dict,
        runner_mode=runner_mode,
        master_bind_host=master_bind_host,
        master_bind_port=master_bind_port,
        master_host=master_host,
        master_port=master_port,
        expected_workers=expected_workers,
        **kwargs,
    )

    return {
        "user_detail": user_detail_dict,
        "user_count": user_count,
        "spawn_rate": spawn_rate,
        "test_time": test_time,
        "web_ui": web_ui_dict,
        "runner_mode": runner_mode,
    }
