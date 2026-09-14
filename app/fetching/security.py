import ipaddress
import re
import socket
from urllib.parse import urlparse


class InsecureUrlException(Exception):
    """Raised when a URL fails security or SSRF validation."""
    pass


FORBIDDEN_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "local",
    "internal",
    "metadata.google.internal",
    "metadata.azure.com",
    "instance-data",
}

FORBIDDEN_HOST_SUFFIXES = (
    ".local",
    ".internal",
    ".localhost",
    ".lan",
    ".home",
    ".corp",
    ".onion",
)

ALLOWED_PORTS = {80, 443, 8080, 8443, None}


def is_safe_url(url: str, allow_private_ips: bool = False) -> bool:
    """Validate that a URL is safe to fetch and does not target internal or private networks."""
    if not url or not isinstance(url, str):
        return False

    url_clean = url.strip()
    try:
        parsed = urlparse(url_clean)
    except Exception:
        return False

    if parsed.scheme.lower() not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    hostname_lower = hostname.lower().strip("[]")

    # 1. Check forbidden hostnames
    if hostname_lower in FORBIDDEN_HOSTS:
        return False

    if any(hostname_lower.endswith(sfx) for sfx in FORBIDDEN_HOST_SUFFIXES):
        return False

    # 2. Check port restrictions (only web ports allowed)
    port = parsed.port
    if port is not None and port not in (80, 443, 8080, 8443):
        return False

    # 3. Check for decimal / octal / hex IP obfuscation (e.g. 2130706433 or 0x7f000001)
    if re.fullmatch(r"^\d+$", hostname_lower) or re.fullmatch(r"^0x[0-9a-fA-F]+$", hostname_lower):
        try:
            val = int(hostname_lower, 0)
            ip = ipaddress.ip_address(val)
            if not allow_private_ips and (
                ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified
            ):
                return False
        except (ValueError, OverflowError):
            return False

    if not allow_private_ips:
        # 4. Check standard IP addresses (IPv4 & IPv6 including IPv4-mapped IPv6)
        try:
            ip = ipaddress.ip_address(hostname_lower)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                return False
            # Check for AWS/GCP metadata specific IP
            if str(ip) == "169.254.169.254":
                return False
            # Check IPv4-mapped IPv6 (e.g., ::ffff:127.0.0.1)
            if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                mapped_ip = ip.ipv4_mapped
                if (
                    mapped_ip.is_private
                    or mapped_ip.is_loopback
                    or mapped_ip.is_link_local
                    or mapped_ip.is_reserved
                ):
                    return False
        except ValueError:
            # Hostname is a regular domain name
            pass

    return True


def validate_url_safety(url: str, allow_private_ips: bool = False) -> None:
    """Raise InsecureUrlException if the URL violates security boundaries."""
    if not is_safe_url(url, allow_private_ips=allow_private_ips):
        raise InsecureUrlException(
            f"URL '{url}' is blocked for security reasons (must be an external HTTP/HTTPS address)."
        )

