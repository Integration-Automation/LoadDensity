from typing import Dict, Any

from je_load_density.wrapper.proxy.user.amqp_user_proxy import ProxyAmqpUser
from je_load_density.wrapper.proxy.user.apns_user_proxy import ProxyApnsUser
from je_load_density.wrapper.proxy.user.async_http_user_proxy import ProxyAsyncHttpUser
from je_load_density.wrapper.proxy.user.cassandra_user_proxy import ProxyCassandraUser
from je_load_density.wrapper.proxy.user.coap_user_proxy import ProxyCoapUser
from je_load_density.wrapper.proxy.user.consul_user_proxy import ProxyConsulUser
from je_load_density.wrapper.proxy.user.couchbase_user_proxy import ProxyCouchbaseUser
from je_load_density.wrapper.proxy.user.elasticsearch_user_proxy import (
    ProxyElasticsearchUser,
)
from je_load_density.wrapper.proxy.user.etcd_user_proxy import ProxyEtcdUser
from je_load_density.wrapper.proxy.user.fast_http_user_proxy import ProxyFastHTTPUser
from je_load_density.wrapper.proxy.user.fcm_user_proxy import ProxyFcmUser
from je_load_density.wrapper.proxy.user.ftp_user_proxy import ProxyFtpUser
from je_load_density.wrapper.proxy.user.fuzz_http_user_proxy import ProxyFuzzHttpUser
from je_load_density.wrapper.proxy.user.graphql_ws_user_proxy import (
    ProxyGraphQLWebSocketUser,
)
from je_load_density.wrapper.proxy.user.grpc_user_proxy import ProxyGrpcUser
from je_load_density.wrapper.proxy.user.http3_user_proxy import ProxyHttp3User
from je_load_density.wrapper.proxy.user.http_user_proxy import ProxyHTTPUser
from je_load_density.wrapper.proxy.user.imap_user_proxy import ProxyImapUser
from je_load_density.wrapper.proxy.user.kafka_user_proxy import ProxyKafkaUser
from je_load_density.wrapper.proxy.user.ldap_user_proxy import ProxyLdapUser
from je_load_density.wrapper.proxy.user.memcached_user_proxy import ProxyMemcachedUser
from je_load_density.wrapper.proxy.user.modbus_user_proxy import ProxyModbusUser
from je_load_density.wrapper.proxy.user.mongo_user_proxy import ProxyMongoUser
from je_load_density.wrapper.proxy.user.mqtt_user_proxy import ProxyMqttUser
from je_load_density.wrapper.proxy.user.nats_user_proxy import ProxyNatsUser
from je_load_density.wrapper.proxy.user.neo4j_user_proxy import ProxyNeo4jUser
from je_load_density.wrapper.proxy.user.opcua_user_proxy import ProxyOpcuaUser
from je_load_density.wrapper.proxy.user.pulsar_user_proxy import ProxyPulsarUser
from je_load_density.wrapper.proxy.user.redis_user_proxy import ProxyRedisUser
from je_load_density.wrapper.proxy.user.sftp_user_proxy import ProxySftpUser
from je_load_density.wrapper.proxy.user.smtp_user_proxy import ProxySmtpUser
from je_load_density.wrapper.proxy.user.snmp_user_proxy import ProxySnmpUser
from je_load_density.wrapper.proxy.user.soap_user_proxy import ProxySoapUser
from je_load_density.wrapper.proxy.user.socket_user_proxy import ProxySocketUser
from je_load_density.wrapper.proxy.user.sql_user_proxy import ProxySqlUser
from je_load_density.wrapper.proxy.user.sse_user_proxy import ProxySseUser
from je_load_density.wrapper.proxy.user.thrift_user_proxy import ProxyThriftUser
from je_load_density.wrapper.proxy.user.vault_user_proxy import ProxyVaultUser
from je_load_density.wrapper.proxy.user.webpush_user_proxy import ProxyWebPushUser
from je_load_density.wrapper.proxy.user.websocket_user_proxy import ProxyWebSocketUser
from je_load_density.wrapper.proxy.user.zmq_user_proxy import ProxyZmqUser


class LocustUserProxy:
    """Locust 使用者代理容器 / per-protocol proxy container."""

    def __init__(self) -> None:
        self.user_dict: Dict[str, Any] = {
            "fast_http_user": ProxyFastHTTPUser(),
            "http_user": ProxyHTTPUser(),
            "async_http_user": ProxyAsyncHttpUser(),
            "http3_user": ProxyHttp3User(),
            "websocket_user": ProxyWebSocketUser(),
            "sse_user": ProxySseUser(),
            "graphql_ws_user": ProxyGraphQLWebSocketUser(),
            "grpc_user": ProxyGrpcUser(),
            "mqtt_user": ProxyMqttUser(),
            "amqp_user": ProxyAmqpUser(),
            "nats_user": ProxyNatsUser(),
            "pulsar_user": ProxyPulsarUser(),
            "coap_user": ProxyCoapUser(),
            "socket_user": ProxySocketUser(),
            "sql_user": ProxySqlUser(),
            "redis_user": ProxyRedisUser(),
            "kafka_user": ProxyKafkaUser(),
            "mongo_user": ProxyMongoUser(),
            "cassandra_user": ProxyCassandraUser(),
            "elasticsearch_user": ProxyElasticsearchUser(),
            "smtp_user": ProxySmtpUser(),
            "imap_user": ProxyImapUser(),
            "ftp_user": ProxyFtpUser(),
            "sftp_user": ProxySftpUser(),
            "fuzz_http_user": ProxyFuzzHttpUser(),
            "soap_user": ProxySoapUser(),
            "ldap_user": ProxyLdapUser(),
            "snmp_user": ProxySnmpUser(),
            "modbus_user": ProxyModbusUser(),
            "opcua_user": ProxyOpcuaUser(),
            "zmq_user": ProxyZmqUser(),
            "thrift_user": ProxyThriftUser(),
            "memcached_user": ProxyMemcachedUser(),
            "neo4j_user": ProxyNeo4jUser(),
            "couchbase_user": ProxyCouchbaseUser(),
            "etcd_user": ProxyEtcdUser(),
            "consul_user": ProxyConsulUser(),
            "vault_user": ProxyVaultUser(),
            "webpush_user": ProxyWebPushUser(),
            "apns_user": ProxyApnsUser(),
            "fcm_user": ProxyFcmUser(),
        }

    def get_user(self, user_type: str) -> Any:
        return self.user_dict.get(user_type)

    def set_user(self, user_type: str, user_instance: Any) -> None:
        self.user_dict[user_type] = user_instance


locust_wrapper_proxy = LocustUserProxy()
