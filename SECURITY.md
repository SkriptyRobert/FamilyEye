# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please report bugs via public GitHub Issues.**

If you discover a security vulnerability, please report it as follows:

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

### Public / Internet-Facing Deployment

When the server is exposed on a public IP (e.g. API scans, bots):

- **Probe paths** - The backend returns 404 for sensitive/probe paths (e.g. `/.env`, `/.git`, `wp-admin`, `phpmyadmin`, `config.json`) instead of serving the SPA.
- **Security headers** - Responses include `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`.
- **Rate limiting** - Public paths (`/`, `/api/health`, `/api/info`, `/api/trust/*`) are rate-limited per IP (60/min). Login 5/min, register 3/min, pairing 10/min. Set `TRUST_PROXY=1` only when behind a trusted reverse proxy (nginx) so client IP is taken from `X-Forwarded-For`; otherwise the app uses the direct connection IP.
- **API docs** - In production set `DISABLE_DOCS=1` or `BACKEND_ENV=production` to disable `/docs`, `/redoc`, `/openapi.json`.
- **Reverse proxy** - For public deployment use nginx (or similar) in front: TLS termination with a valid certificate (e.g. Let's Encrypt), stricter rate limits, optional WAF. Do not commit `.env`; set `SECRET_KEY`, `POSTGRES_PASSWORD`, `BACKEND_URL` in environment.

## Known Security Considerations

### PIN Storage (Android Agent)
The Android agent uses SHA-256 for local PIN storage. For enhanced security in future versions, we plan to migrate to bcrypt with device-specific salt.

### Self-Signed Certificates
For local network deployments, self-signed certificates are acceptable. For public deployments, use Let's Encrypt or similar CA.

### Logging
Do not log full tokens, API keys, or passwords. Log only prefixes (e.g. first 8 characters) or omit sensitive fields.

---

Thank you for helping keep FamilyEye secure!
