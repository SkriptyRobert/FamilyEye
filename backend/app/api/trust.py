"""Trust API endpoints for certificate distribution."""
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
import base64
import io

router = APIRouter()


@router.get("/ca.crt", response_class=PlainTextResponse)
async def download_ca_certificate():
    """
    Download the FamilyEye Root CA certificate.
    Users install this certificate to trust the server.
    """
    from ..ssl_manager import get_ca_certificate_pem, generate_certificates, certificates_exist
    
    # Generate certificates if they don't exist
    if not certificates_exist():
        generate_certificates()
    
    ca_pem = get_ca_certificate_pem()
    if ca_pem:
        return Response(
            content=ca_pem,
            media_type="application/x-x509-ca-cert",
            headers={
                "Content-Disposition": "attachment; filename=FamilyEye-CA.crt"
            }
        )
    else:
        return PlainTextResponse("Certificate not available", status_code=404)


@router.get("/info")
async def get_trust_info():
    """
    Get information about SSL/TLS configuration.
    """
    from ..ssl_manager import get_certificate_info, get_local_ip
    import socket
    
    info = get_certificate_info()
    
    # Add download URL - use settings.BACKEND_URL if configured, otherwise local IP
    from ..config import settings
    local_ip = get_local_ip()
    
    # Check if BACKEND_URL is set and not default localhost
    backend_url = settings.BACKEND_URL
    if backend_url and "localhost" not in backend_url and "127.0.0.1" not in backend_url:
        # Use configured BACKEND_URL
        info["download_url"] = f"{backend_url}/api/trust/ca.crt"
        info["qr_url"] = f"{backend_url}/api/trust/qr.png"
    else:
        # Fallback to local IP with default port
        port = 8000
        info["download_url"] = f"https://{local_ip}:{port}/api/trust/ca.crt"
        info["qr_url"] = f"https://{local_ip}:{port}/api/trust/qr.png"
    
    return info


@router.get("/qr.png")
async def get_qr_code():
    """
    Get QR code for easy CA certificate installation.
    Scan this QR code with your mobile device to download and install the CA.
    """
    from ..ssl_manager import get_local_ip, certificates_exist, generate_certificates
    
    # Generate certificates if they don't exist
    if not certificates_exist():
        generate_certificates()
    
    try:
        import qrcode
        from PIL import Image
        
        local_ip = get_local_ip()
        
        # Use settings.BACKEND_URL if configured, otherwise local IP
        from ..config import settings
        backend_url = settings.BACKEND_URL
        if backend_url and "localhost" not in backend_url and "127.0.0.1" not in backend_url:
            cert_url = f"{backend_url}/api/trust/ca.crt"
        else:
            port = 8000
            cert_url = f"https://{local_ip}:{port}/api/trust/ca.crt"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(cert_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        return Response(
            content=img_buffer.getvalue(),
            media_type="image/png",
            headers={
                "Cache-Control": "no-cache"
            }
        )
        
    except ImportError:
        # qrcode or PIL not installed, return text instead
        from ..ssl_manager import get_local_ip
        from ..config import settings
        local_ip = get_local_ip()
        
        backend_url = settings.BACKEND_URL
        if backend_url and "localhost" not in backend_url and "127.0.0.1" not in backend_url:
            download_url = f"{backend_url}/api/trust/ca.crt"
        else:
            download_url = f"https://{local_ip}:8000/api/trust/ca.crt"
        
        return PlainTextResponse(
            f"QR code library not installed.\n\n"
            f"Install manually: pip install qrcode[pil]\n\n"
            f"Or download certificate from:\n"
            f"{download_url}",
            status_code=200
        )


@router.get("/status")
async def get_ssl_status():
    """
    Check if SSL is enabled and working.
    """
    from ..ssl_manager import certificates_exist, get_certificate_info
    
    return {
        "ssl_enabled": certificates_exist(),
        "certificates": get_certificate_info()
    }
