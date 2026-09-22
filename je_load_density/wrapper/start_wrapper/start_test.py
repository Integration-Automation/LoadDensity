from typing import Any, Dict, Optional

from je_load_density.utils.logging.loggin_instance import load_density_logger
from je_load_density.wrapper.create_locust_env.create_locust_env import prepare_env
from je_load_density.wrapper.user_template.amqp_user_template import (
    AmqpUserWrapper,
    set_wrapper_amqp_user,
)
from je_load_density.wrapper.user_template.async_http_user_template import (
    AsyncHttpUserWrapper,
    set_wrapper_async_http_user,
)
from je_load_density.wrapper.user_template.cassandra_user_template import (
    CassandraUserWrapper,
    set_wrapper_cassandra_user,
)
from je_load_density.wrapper.user_template.coap_user_template import (
    CoapUserWrapper,
    set_wrapper_coap_user,
)
from je_load_density.wrapper.user_template.elasticsearch_user_template import (
    ElasticsearchUserWrapper,
    set_wrapper_elasticsearch_user,
)
from je_load_density.wrapper.user_template.fast_http_user_template import (
    FastHttpUserWrapper,
    set_wrapper_fasthttp_user,
)
from je_load_density.wrapper.user_template.ftp_user_template import (
    FtpUserWrapper,
    set_wrapper_ftp_user,
)
from je_load_density.wrapper.user_template.fuzz_http_user_template import (
    FuzzHttpUserWrapper,
    set_wrapper_fuzz_http_user,
)
from je_load_density.wrapper.user_template.graphql_ws_user_template import (
    GraphQLWebSocketUserWrapper,
    set_wrapper_graphql_ws_user,
)
from je_load_density.wrapper.user_template.grpc_user_template import (
    GrpcUserWrapper,
    set_wrapper_grpc_user,
)
from je_load_density.wrapper.user_template.http3_user_template import (
    Http3UserWrapper,
    set_wrapper_http3_user,
)
from je_load_density.wrapper.user_template.http_user_template import (
    HttpUserWrapper,
    set_wrapper_http_user,
)
from je_load_density.wrapper.user_template.imap_user_template import (
    ImapUserWrapper,
    set_wrapper_imap_user,
)
from je_load_density.wrapper.user_template.kafka_user_template import (
    KafkaUserWrapper,
    set_wrapper_kafka_user,
)
from je_load_density.wrapper.user_template.mongo_user_template import (
    MongoUserWrapper,
    set_wrapper_mongo_user,
)
from je_load_density.wrapper.user_template.mqtt_user_template import (
    MqttUserWrapper,
    set_wrapper_mqtt_user,
)
from je_load_density.wrapper.user_template.nats_user_template import (
    NatsUserWrapper,
    set_wrapper_nats_user,
)
from je_load_density.wrapper.user_template.pulsar_user_template import (
    PulsarUserWrapper,
    set_wrapper_pulsar_user,
)
from je_load_density.wrapper.user_template.redis_user_template import (
    RedisUserWrapper,
    set_wrapper_redis_user,
)
from je_load_density.wrapper.user_template.sftp_user_template import (
    SftpUserWrapper,
    set_wrapper_sftp_user,
)
from je_load_density.wrapper.user_template.smtp_user_template import (
    SmtpUserWrapper,
    set_wrapper_smtp_user,
)
from je_load_density.wrapper.user_template.socket_user_template import (
    SocketUserWrapper,
    set_wrapper_socket_user,
)
from je_load_density.wrapper.user_template.sql_user_template import (
    SqlUserWrapper,
    set_wrapper_sql_user,
)
from je_load_density.wrapper.user_template.sse_user_template import (
    SseUserWrapper,
    set_wrapper_sse_user,
)
from je_load_density.wrapper.user_template.apns_user_template import (
    ApnsUserWrapper,
    set_wrapper_apns_user,
)
from je_load_density.wrapper.user_template.consul_user_template import (
    ConsulUserWrapper,
    set_wrapper_consul_user,
)
from je_load_density.wrapper.user_template.couchbase_user_template import (
    CouchbaseUserWrapper,
    set_wrapper_couchbase_user,
)
from je_load_density.wrapper.user_template.etcd_user_template import (
    EtcdUserWrapper,
    set_wrapper_etcd_user,
)
from je_load_density.wrapper.user_template.fcm_user_template import (
    FcmUserWrapper,
    set_wrapper_fcm_user,
)
from je_load_density.wrapper.user_template.ldap_user_template import (
    LdapUserWrapper,
    set_wrapper_ldap_user,
)
from je_load_density.wrapper.user_template.memcached_user_template import (
    MemcachedUserWrapper,
    set_wrapper_memcached_user,
)
from je_load_density.wrapper.user_template.modbus_user_template import (
    ModbusUserWrapper,
    set_wrapper_modbus_user,
)
from je_load_density.wrapper.user_template.neo4j_user_template import (
    Neo4jUserWrapper,
    set_wrapper_neo4j_user,
)
from je_load_density.wrapper.user_template.opcua_user_template import (
    OpcuaUserWrapper,
    set_wrapper_opcua_user,
)
from je_load_density.wrapper.user_template.snmp_user_template import (
    SnmpUserWrapper,
    set_wrapper_snmp_user,
)
from je_load_density.wrapper.user_template.soap_user_template import (
    SoapUserWrapper,
    set_wrapper_soap_user,
)
from je_load_density.wrapper.user_template.thrift_user_template import (
    ThriftUserWrapper,
    set_wrapper_thrift_user,
)
from je_load_density.wrapper.user_template.vault_user_template import (
    VaultUserWrapper,
    set_wrapper_vault_user,
)
from je_load_density.wrapper.user_template.webpush_user_template import (
    WebPushUserWrapper,
    set_wrapper_webpush_user,
)
from je_load_density.wrapper.user_template.websocket_user_template import (
    WebSocketUserWrapper,
    set_wrapper_websocket_user,
)
from je_load_density.wrapper.user_template.zmq_user_template import (
    ZmqUserWrapper,
    set_wrapper_zmq_user,
)


_USER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "fast_http_user": {"actually_user": FastHttpUserWrapper, "init": set_wrapper_fasthttp_user},
    "http_user": {"actually_user": HttpUserWrapper, "init": set_wrapper_http_user},
    "async_http_user": {"actually_user": AsyncHttpUserWrapper, "init": set_wrapper_async_http_user},
    "http3_user": {"actually_user": Http3UserWrapper, "init": set_wrapper_http3_user},
    "websocket_user": {"actually_user": WebSocketUserWrapper, "init": set_wrapper_websocket_user},
    "sse_user": {"actually_user": SseUserWrapper, "init": set_wrapper_sse_user},
    "graphql_ws_user": {
        "actually_user": GraphQLWebSocketUserWrapper,
        "init": set_wrapper_graphql_ws_user,
    },
    "grpc_user": {"actually_user": GrpcUserWrapper, "init": set_wrapper_grpc_user},
    "mqtt_user": {"actually_user": MqttUserWrapper, "init": set_wrapper_mqtt_user},
    "amqp_user": {"actually_user": AmqpUserWrapper, "init": set_wrapper_amqp_user},
    "nats_user": {"actually_user": NatsUserWrapper, "init": set_wrapper_nats_user},
    "pulsar_user": {"actually_user": PulsarUserWrapper, "init": set_wrapper_pulsar_user},
    "coap_user": {"actually_user": CoapUserWrapper, "init": set_wrapper_coap_user},
    "socket_user": {"actually_user": SocketUserWrapper, "init": set_wrapper_socket_user},
    "sql_user": {"actually_user": SqlUserWrapper, "init": set_wrapper_sql_user},
    "redis_user": {"actually_user": RedisUserWrapper, "init": set_wrapper_redis_user},
    "kafka_user": {"actually_user": KafkaUserWrapper, "init": set_wrapper_kafka_user},
    "mongo_user": {"actually_user": MongoUserWrapper, "init": set_wrapper_mongo_user},
    "cassandra_user": {
        "actually_user": CassandraUserWrapper,
        "init": set_wrapper_cassandra_user,
    },
    "elasticsearch_user": {
        "actually_user": ElasticsearchUserWrapper,
        "init": set_wrapper_elasticsearch_user,
    },
    "smtp_user": {"actually_user": SmtpUserWrapper, "init": set_wrapper_smtp_user},
    "imap_user": {"actually_user": ImapUserWrapper, "init": set_wrapper_imap_user},
    "ftp_user": {"actually_user": FtpUserWrapper, "init": set_wrapper_ftp_user},
    "sftp_user": {"actually_user": SftpUserWrapper, "init": set_wrapper_sftp_user},
    "fuzz_http_user": {
        "actually_user": FuzzHttpUserWrapper,
        "init": set_wrapper_fuzz_http_user,
    },
    "soap_user": {"actually_user": SoapUserWrapper, "init": set_wrapper_soap_user},
    "ldap_user": {"actually_user": LdapUserWrapper, "init": set_wrapper_ldap_user},
    "snmp_user": {"actually_user": SnmpUserWrapper, "init": set_wrapper_snmp_user},
    "modbus_user": {"actually_user": ModbusUserWrapper, "init": set_wrapper_modbus_user},
    "opcua_user": {"actually_user": OpcuaUserWrapper, "init": set_wrapper_opcua_user},
    "zmq_user": {"actually_user": ZmqUserWrapper, "init": set_wrapper_zmq_user},
    "thrift_user": {"actually_user": ThriftUserWrapper, "init": set_wrapper_thrift_user},
    "memcached_user": {
        "actually_user": MemcachedUserWrapper,
        "init": set_wrapper_memcached_user,
    },
    "neo4j_user": {"actually_user": Neo4jUserWrapper, "init": set_wrapper_neo4j_user},
    "couchbase_user": {
        "actually_user": CouchbaseUserWrapper,
        "init": set_wrapper_couchbase_user,
    },
    "etcd_user": {"actually_user": EtcdUserWrapper, "init": set_wrapper_etcd_user},
    "consul_user": {"actually_user": ConsulUserWrapper, "init": set_wrapper_consul_user},
    "vault_user": {"actually_user": VaultUserWrapper, "init": set_wrapper_vault_user},
    "webpush_user": {"actually_user": WebPushUserWrapper, "init": set_wrapper_webpush_user},
    "apns_user": {"actually_user": ApnsUserWrapper, "init": set_wrapper_apns_user},
    "fcm_user": {"actually_user": FcmUserWrapper, "init": set_wrapper_fcm_user},
}


def _pop_distributed_config(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract Locust distributed-runner fields from ``**kwargs``.

    Keeping these in kwargs (rather than as positional parameters) lets
    callers stay backwards-compatible while satisfying the public-API
    parameter budget.
    """
    return {
        "master_bind_host": kwargs.pop("master_bind_host", "*"),
        "master_bind_port": kwargs.pop("master_bind_port", 5557),
        "master_host": kwargs.pop("master_host", "127.0.0.1"),
        "master_port": kwargs.pop("master_port", 5557),
        "expected_workers": kwargs.pop("expected_workers", 0),
    }


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
    """
    啟動壓力測試。Start load test.

    ``runner_mode`` is ``"local"`` | ``"master"`` | ``"worker"``.
    Distributed-mode fields (``master_bind_host`` / ``master_bind_port`` /
    ``master_host`` / ``master_port`` / ``expected_workers``) are
    accepted via ``**kwargs`` so the signature stays under the public
    API parameter budget.
    """
    distributed = _pop_distributed_config(kwargs)
    load_density_logger.info(
        f"start_test, user_detail_dict={user_detail_dict}, user_count={user_count}, "
        f"spawn_rate={spawn_rate}, test_time={test_time}, web_ui_dict={web_ui_dict}, "
        f"runner_mode={runner_mode}, distributed={distributed}, params={kwargs}"
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
        load_shape=load_shape,
        shape_config=shape_config,
        **distributed,
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
