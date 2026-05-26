from je_load_density.wrapper.user_template.request_executor import _build_kwargs


def test_build_kwargs_passes_cert_through():
    kwargs = _build_kwargs({"method": "get", "cert": "/etc/ssl/client.pem"})
    assert kwargs["cert"] == "/etc/ssl/client.pem"


def test_build_kwargs_accepts_client_cert_alias_as_cert():
    kwargs = _build_kwargs({"method": "get",
                             "client_cert": ("/etc/ssl/c.pem", "/etc/ssl/k.pem")})
    assert kwargs["cert"] == ("/etc/ssl/c.pem", "/etc/ssl/k.pem")


def test_build_kwargs_cert_takes_precedence_over_client_cert():
    kwargs = _build_kwargs({"method": "get",
                             "cert": "/explicit.pem",
                             "client_cert": "/alias.pem"})
    assert kwargs["cert"] == "/explicit.pem"
