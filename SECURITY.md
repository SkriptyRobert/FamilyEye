# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, please report it by:

1. **Email:** Send details to **robert.pesout@gmail.com** (Róbert Pešout, BertSoftware)
2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to Expect

- **Response Time:** We aim to respond within 48 hours
- **Updates:** We will keep you informed of our progress
- **Credit:** We're happy to credit you in the fix (if desired)

## Security Best Practices

When deploying FamilyEye:

1. **Always set `SECRET_KEY`** - Never use the default in production
2. **Use HTTPS** - Place valid SSL certificates in `certs/`
3. **Secure the database** - Keep `parental_control.db` encrypted or protected
4. **Keep updated** - Regularly update to the latest version

## Known Security Considerations

### PIN Storage (Android Agent)
The Android agent uses SHA-256 for local PIN storage. For enhanced security in future versions, we plan to migrate to bcrypt with device-specific salt.

### Self-Signed Certificates
For local network deployments, self-signed certificates are acceptable. For public deployments, use Let's Encrypt or similar CA.

---

Thank you for helping keep FamilyEye secure! 🔐
