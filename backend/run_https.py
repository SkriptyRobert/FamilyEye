#!/usr/bin/env python3
"""
FamilyEye Backend Launcher with HTTPS support.
Automatically generates SSL certificates and starts the server.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    import uvicorn
    from app.config import settings
    from app.ssl_manager import certificates_exist, generate_certificates, get_ssl_context, get_local_ip
    
    # Check for custom certificates (advanced users)
    custom_cert = os.environ.get("SSL_CERT_FILE")
    custom_key = os.environ.get("SSL_KEY_FILE")
    
    ssl_keyfile = None
    ssl_certfile = None
    
    if custom_cert and custom_key and os.path.exists(custom_cert) and os.path.exists(custom_key):
        # Use custom certificates
        print(f"Using custom SSL certificates:")
        print(f"  Certificate: {custom_cert}")
        print(f"  Key: {custom_key}")
        ssl_certfile = custom_cert
        ssl_keyfile = custom_key
    else:
        # Generate or use existing FamilyEye certificates
        if not certificates_exist():
            print("Generating FamilyEye SSL certificates...")
            if generate_certificates():
                print("SSL certificates generated successfully!")
            else:
                print("WARNING: Failed to generate SSL certificates. Running without HTTPS.")
        
        ssl_ctx = get_ssl_context()
        if ssl_ctx:
            ssl_certfile, ssl_keyfile = ssl_ctx
    
    local_ip = get_local_ip()
    port = settings.PORT
    
    print("\n" + "="*60)
    print("  FamilyEye Backend Server")
    print("="*60)
    
    if ssl_certfile and ssl_keyfile:
        print(f"  🔒 HTTPS enabled")
        print(f"  📍 Local:   https://localhost:{port}")
        print(f"  📍 Network: https://{local_ip}:{port}")
        print(f"\n  📱 For mobile setup, scan QR code at:")
        print(f"     https://{local_ip}:{port}/api/trust/qr.png")
        print(f"\n  📥 Or download CA certificate:")
        print(f"     https://{local_ip}:{port}/api/trust/ca.crt")
    else:
        print(f"  ⚠️  HTTP mode (not encrypted)")
        print(f"  📍 Local:   http://localhost:{port}")
        print(f"  📍 Network: http://{local_ip}:{port}")
    
    print("="*60 + "\n")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
