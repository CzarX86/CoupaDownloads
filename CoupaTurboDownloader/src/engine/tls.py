"""TLS configuration for enterprise-managed Windows hosts."""

from __future__ import annotations

import ssl


def system_ssl_context() -> ssl.SSLContext:
    """Use the operating-system trust store when the truststore package exists.

    Corporate Windows devices commonly install the Coupa proxy CA in the
    Windows certificate store, while httpx otherwise uses certifi only.
    """
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()
