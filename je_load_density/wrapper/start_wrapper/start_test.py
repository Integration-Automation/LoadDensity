"""Compatible start-test path with explicit, lazy scheduler selection."""

import importlib

from je_load_density.engine.entrypoints import start_test as start_test

_LEGACY_NAMES = frozenset(
    [
        "AmqpUserWrapper",
        "Any",
        "ApnsUserWrapper",
        "AsyncHttpUserWrapper",
        "CassandraUserWrapper",
        "CoapUserWrapper",
        "ConsulUserWrapper",
        "CouchbaseUserWrapper",
        "Dict",
        "ElasticsearchUserWrapper",
        "EtcdUserWrapper",
        "FastHttpUserWrapper",
        "FcmUserWrapper",
        "FtpUserWrapper",
        "FuzzHttpUserWrapper",
        "GraphQLWebSocketUserWrapper",
        "GrpcUserWrapper",
        "Http3UserWrapper",
        "HttpUserWrapper",
        "ImapUserWrapper",
        "KafkaUserWrapper",
        "LdapUserWrapper",
        "MemcachedUserWrapper",
        "ModbusUserWrapper",
        "MongoUserWrapper",
        "MqttUserWrapper",
        "NatsUserWrapper",
        "Neo4jUserWrapper",
        "OpcuaUserWrapper",
        "Optional",
        "PulsarUserWrapper",
        "RedisUserWrapper",
        "SftpUserWrapper",
        "SmtpUserWrapper",
        "SnmpUserWrapper",
        "SoapUserWrapper",
        "SocketUserWrapper",
        "SqlUserWrapper",
        "SseUserWrapper",
        "ThriftUserWrapper",
        "VaultUserWrapper",
        "WebPushUserWrapper",
        "WebSocketUserWrapper",
        "ZmqUserWrapper",
        "_USER_REGISTRY",
        "_pop_distributed_config",
        "load_density_logger",
        "prepare_env",
        "set_wrapper_amqp_user",
        "set_wrapper_apns_user",
        "set_wrapper_async_http_user",
        "set_wrapper_cassandra_user",
        "set_wrapper_coap_user",
        "set_wrapper_consul_user",
        "set_wrapper_couchbase_user",
        "set_wrapper_elasticsearch_user",
        "set_wrapper_etcd_user",
        "set_wrapper_fasthttp_user",
        "set_wrapper_fcm_user",
        "set_wrapper_ftp_user",
        "set_wrapper_fuzz_http_user",
        "set_wrapper_graphql_ws_user",
        "set_wrapper_grpc_user",
        "set_wrapper_http3_user",
        "set_wrapper_http_user",
        "set_wrapper_imap_user",
        "set_wrapper_kafka_user",
        "set_wrapper_ldap_user",
        "set_wrapper_memcached_user",
        "set_wrapper_modbus_user",
        "set_wrapper_mongo_user",
        "set_wrapper_mqtt_user",
        "set_wrapper_nats_user",
        "set_wrapper_neo4j_user",
        "set_wrapper_opcua_user",
        "set_wrapper_pulsar_user",
        "set_wrapper_redis_user",
        "set_wrapper_sftp_user",
        "set_wrapper_smtp_user",
        "set_wrapper_snmp_user",
        "set_wrapper_soap_user",
        "set_wrapper_socket_user",
        "set_wrapper_sql_user",
        "set_wrapper_sse_user",
        "set_wrapper_thrift_user",
        "set_wrapper_vault_user",
        "set_wrapper_webpush_user",
        "set_wrapper_websocket_user",
        "set_wrapper_zmq_user",
    ]
)


def __getattr__(name: str):
    if name not in _LEGACY_NAMES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    implementation = importlib.import_module("je_load_density.wrapper.start_wrapper.locust_start")
    value = getattr(implementation, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | _LEGACY_NAMES)


__all__ = ["start_test", *(name for name in sorted(_LEGACY_NAMES) if not name.startswith("_"))]
