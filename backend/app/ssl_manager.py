"""
FamilyEye Trust SSL Manager.
Automatically generates and manages SSL certificates for secure communication.
"""
import os
import socket
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import logging

logger = logging.getLogger("ssl_manager")

# Certificate storage directory
CERTS_DIR = Path(__file__).parent.parent.parent / "certs"
CA_KEY_FILE = CERTS_DIR / "familyeye-ca.key"
CA_CERT_FILE = CERTS_DIR / "familyeye-ca.crt"
SERVER_KEY_FILE = CERTS_DIR / "server.key"
SERVER_CERT_FILE = CERTS_DIR / "server.crt"


def ensure_certs_dir():
    """Create certificates directory if it doesn't exist."""
    CERTS_DIR.mkdir(parents=True, exist_ok=True)


def get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def certificates_exist() -> bool:
    """Check if all required certificates exist."""
    return all([
        CA_KEY_FILE.exists(),
        CA_CERT_FILE.exists(),
        SERVER_KEY_FILE.exists(),
        SERVER_CERT_FILE.exists()
    ])


def generate_certificates(common_name: str = "FamilyEye", validity_days: int = 3650) -> bool:
    """
    Generate CA and server certificates.
    
    Args:
        common_name: Name for the CA certificate
        validity_days: How long the certificates are valid (default 10 years)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        
        ensure_certs_dir()
        local_ip = get_local_ip()
        hostname = socket.gethostname()
        
        logger.info(f"Generating certificates for {hostname} ({local_ip})")
        
        # === Generate CA Key and Certificate ===
        ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        ca_subject = ca_issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CZ"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FamilyEye"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{common_name} Root CA"),
        ])
        
        ca_cert = (
            x509.CertificateBuilder()
            .subject_name(ca_subject)
            .issuer_name(ca_issuer)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=validity_days))
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(ca_key, hashes.SHA256(), default_backend())
        )
        
        # Save CA key and certificate
        with open(CA_KEY_FILE, "wb") as f:
            f.write(ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        with open(CA_CERT_FILE, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
        
        logger.info(f"CA certificate saved to {CA_CERT_FILE}")
        
        # === Generate Server Key and Certificate ===
        server_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        server_subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CZ"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FamilyEye"),
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ])
        
        # Subject Alternative Names (SAN) - important for browsers
        import ipaddress
        san_list = [
            x509.DNSName("localhost"),
            x509.DNSName(hostname),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]
        
        # Add local IP if different from localhost
        if local_ip != "127.0.0.1":
            try:
                san_list.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
            except Exception:
                pass
        
        server_cert = (
            x509.CertificateBuilder()
            .subject_name(server_subject)
            .issuer_name(ca_cert.subject)
            .public_key(server_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=validity_days))
            .add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .sign(ca_key, hashes.SHA256(), default_backend())
        )
        
        # Save server key and certificate
        with open(SERVER_KEY_FILE, "wb") as f:
            f.write(server_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        with open(SERVER_CERT_FILE, "wb") as f:
            f.write(server_cert.public_bytes(serialization.Encoding.PEM))
        
        logger.info(f"Server certificate saved to {SERVER_CERT_FILE}")
        logger.info("SSL certificates generated successfully!")
        
        return True
        
    except ImportError:
        logger.error("cryptography package not installed. Run: pip install cryptography")
        return False
    except Exception as e:
        logger.error(f"Failed to generate certificates: {e}")
        return False


def get_ca_certificate_pem() -> Optional[str]:
    """Get CA certificate as PEM string for download."""
    if CA_CERT_FILE.exists():
        return CA_CERT_FILE.read_text()
    return None


def get_ssl_context() -> Optional[Tuple[str, str]]:
    """
    Get SSL context for uvicorn.
    
    Returns:
        Tuple of (cert_file, key_file) paths or None if not available
    """
    if not certificates_exist():
        if not generate_certificates():
            return None
    
    return (str(SERVER_CERT_FILE), str(SERVER_KEY_FILE))


def get_certificate_info() -> dict:
    """Get information about current certificates."""
    info = {
        "ssl_enabled": certificates_exist(),
        "ca_cert_path": str(CA_CERT_FILE) if CA_CERT_FILE.exists() else None,
        "server_cert_path": str(SERVER_CERT_FILE) if SERVER_CERT_FILE.exists() else None,
        "local_ip": get_local_ip(),
        "hostname": socket.gethostname(),
    }
    
    if CA_CERT_FILE.exists():
        try:
            from cryptography import x509
            cert_data = CA_CERT_FILE.read_bytes()
            cert = x509.load_pem_x509_certificate(cert_data)
            info["ca_valid_until"] = cert.not_valid_after.isoformat()
            info["ca_subject"] = cert.subject.rfc4514_string()
        except Exception:
            pass
    
    return info
