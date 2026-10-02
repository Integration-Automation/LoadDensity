"""Local protocol/codec capabilities; service integration checks run separately."""

import tempfile
from pathlib import Path


def amqp() -> None:
    import pika

    if pika.ConnectionParameters(host="127.0.0.1", socket_timeout=1).host != "127.0.0.1":
        raise RuntimeError("AMQP connection configuration failed")


def cassandra() -> None:
    from cassandra.cluster import Cluster

    cluster = Cluster(contact_points=["127.0.0.1"], connect_timeout=1)
    cluster.shutdown()


def coap() -> None:
    from aiocoap import GET, Message

    message = Message(code=GET, mtype=0, mid=1, uri="coap://localhost/health")
    if Message.decode(message.encode()).code != GET:
        raise RuntimeError("CoAP codec round-trip failed")


def couchbase() -> None:
    from couchbase.transcoder import RawJSONTranscoder

    encoded, flags = RawJSONTranscoder().encode_value(b'{"ok":true}')
    if not encoded or not flags:
        raise RuntimeError("Couchbase JSON transcoder failed")


def elasticsearch() -> None:
    from elasticsearch import Elasticsearch

    client = Elasticsearch("http://127.0.0.1:9", request_timeout=1)
    client.options(request_timeout=1)
    client.close()


def etcd() -> None:
    from je_load_density.wrapper.user_template.etcd_user_template import _import_etcd3

    sdk = _import_etcd3()
    if sdk.__name__ != "etcd3gw":
        raise RuntimeError("The installed etcd extra must provide the gateway client")
    client = sdk.client(host="127.0.0.1", port=9, timeout=1, api_path="/v3/")
    if not client.get_url("kv/range").endswith("/v3/kv/range"):
        raise RuntimeError("etcd gateway API configuration failed")
    client.session.close()


def grpc() -> None:
    import grpc as grpc_sdk

    with grpc_sdk.insecure_channel("127.0.0.1:9") as channel:
        channel.unary_unary("/smoke.Service/Check")


def http2() -> None:
    import asyncio

    import httpx

    async def configure() -> None:
        async with httpx.AsyncClient(http2=True):
            pass

    asyncio.run(configure())


def http3() -> None:
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.connection import QuicConnection

    connection = QuicConnection(configuration=QuicConfiguration(is_client=True, alpn_protocols=["h3"]))
    connection.connect(("127.0.0.1", 443), now=0)
    if not connection.datagrams_to_send(now=0):
        raise RuntimeError("QUIC did not generate a client handshake")


def kafka() -> None:
    from kafka.protocol.metadata import MetadataRequest

    if not MetadataRequest[0]([]).encode():
        raise RuntimeError("Kafka metadata request encoding failed")


def ldap() -> None:
    from ldap3 import MOCK_SYNC, Connection, Server

    connection = Connection(Server("127.0.0.1"), client_strategy=MOCK_SYNC)
    if not connection.bind():
        raise RuntimeError("LDAP mock bind failed")
    connection.unbind()


def memcached() -> None:
    from pymemcache.client.base import Client

    client = Client(("127.0.0.1", 9), connect_timeout=1, timeout=1)
    client.close()


def modbus() -> None:
    from pymodbus.client import ModbusTcpClient
    from pymodbus.pdu.register_message import ReadHoldingRegistersRequest

    if not ReadHoldingRegistersRequest(address=0, count=1).encode():
        raise RuntimeError("Modbus request encoding failed")
    ModbusTcpClient("127.0.0.1", port=9, timeout=1).close()


def mongo() -> None:
    from pymongo import MongoClient

    with MongoClient("mongodb://127.0.0.1:9", connect=False) as client:
        if client.codec_options.document_class is not dict:
            raise RuntimeError("MongoDB document codec configuration failed")


def mqtt() -> None:
    from paho.mqtt.client import CallbackAPIVersion, Client, topic_matches_sub

    Client(CallbackAPIVersion.VERSION2, client_id="loaddensity-smoke").user_data_set({"smoke": True})
    if not topic_matches_sub("smoke/+", "smoke/check"):
        raise RuntimeError("MQTT topic matching failed")


def nats() -> None:
    import asyncio

    from nats.aio.client import Client

    client = Client()
    if client.is_connected:
        raise RuntimeError("A new NATS client unexpectedly connects")
    asyncio.run(client.close())


def neo4j() -> None:
    from neo4j import GraphDatabase

    with GraphDatabase.driver("bolt://127.0.0.1:9", auth=None, connection_timeout=1):
        pass


def opcua() -> None:
    from asyncua import ua
    from asyncua.ua import ua_binary

    if not ua_binary.nodeid_to_binary(ua.NodeId(123, 2)):
        raise RuntimeError("OPC UA node encoding failed")


def pulsar() -> None:
    import pulsar as pulsar_sdk

    client = pulsar_sdk.Client("pulsar://127.0.0.1:9", operation_timeout_seconds=1)
    client.close()


def redis() -> None:
    import redis as redis_sdk

    client = redis_sdk.Redis(host="127.0.0.1", port=9, socket_timeout=1)
    connection = client.connection_pool.make_connection()
    try:
        if b"PING" not in b"".join(connection.pack_command("PING")):
            raise RuntimeError("Redis command encoding failed")
    finally:
        connection.disconnect()
        client.close()


def sftp() -> None:
    import paramiko

    if not paramiko.RSAKey.generate(2048).asbytes():
        raise RuntimeError("SSH key encoding failed")


def snmp() -> None:
    from pysnmp.hlapi.v3arch.asyncio import SnmpEngine

    SnmpEngine().close_dispatcher()


def sql() -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine("sqlite://")
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT 1")).scalar() != 1:
                raise RuntimeError("SQL local query failed")
    finally:
        engine.dispose()


def thrift() -> None:
    import thriftpy2
    from thriftpy2.protocol import TBinaryProtocol
    from thriftpy2.transport import TMemoryBuffer

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "smoke.thrift"
        path.write_text("struct Check { 1: string name }", encoding="utf-8")
        module = thriftpy2.load(str(path), module_name="smoke_thrift")
        transport = TMemoryBuffer()
        module.Check(name="smoke").write(TBinaryProtocol(transport))
        if not transport.getvalue():
            raise RuntimeError("Thrift message encoding failed")


def webpush() -> None:
    from py_vapid import Vapid02
    from pywebpush import WebPushException

    vapid = Vapid02()
    vapid.generate_keys()
    headers = vapid.sign({"aud": "https://localhost", "sub": "mailto:smoke@example.invalid"})
    if "Authorization" not in headers or not isinstance(WebPushException("smoke"), Exception):
        raise RuntimeError("Web Push authorization encoding failed")


def websocket() -> None:
    from websocket import ABNF

    if len(ABNF.create_frame("smoke", ABNF.OPCODE_TEXT).format()) <= len("smoke"):
        raise RuntimeError("WebSocket framing failed")


def zmq() -> None:
    import zmq as zmq_sdk

    with zmq_sdk.Context() as context:
        with context.socket(zmq_sdk.PAIR) as sender, context.socket(zmq_sdk.PAIR) as receiver:
            sender.bind("inproc://loaddensity-smoke")
            receiver.connect("inproc://loaddensity-smoke")
            sender.send(b"smoke")
            if receiver.recv() != b"smoke":
                raise RuntimeError("ZeroMQ local exchange failed")
