"""
Email service using Resend for sending invitation emails.
"""

import logging

from ..config import settings

logger = logging.getLogger(__name__)

# Only import resend if API key is configured
_resend = None


def _get_resend():
    """Lazy load resend module."""
    global _resend
    if _resend is None:
        try:
            import resend
            if settings.resend_api_key:
                resend.api_key = settings.resend_api_key
            _resend = resend
        except ImportError:
            logger.warning("Resend module not installed")
            return None
    return _resend


def is_email_configured() -> bool:
    """Check if email sending is configured."""
    return bool(settings.resend_api_key)


def send_invitation_email(
    to_email: str,
    invite_token: str,
    invited_by_name: str,
    role: str,
    expires_hours: int = 72
) -> str | None:
    """
    Send an invitation email to a new user.
    
    Returns the email ID if successful, None if failed or not configured.
    """
    if not is_email_configured():
        logger.warning(f"Email not configured - invitation for {to_email} not sent")
        return None

    resend = _get_resend()
    if not resend:
        return None

    # Build the invitation URL
    invite_url = f"{settings.application_url}/accept-invite?token={invite_token}"

    # Role display name
    role_display = {
        "member": "Member",
        "admin": "Admin"
    }.get(role, role)

    # HTML email template
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You're Invited to Cartographer</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f1f5f9;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f1f5f9;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 40px 24px; text-align: center; background: linear-gradient(135deg, #0891b2 0%, #0e7490 100%); border-radius: 12px 12px 0 0;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600;">🗺️ Cartographer</h1>
                            <p style="margin: 8px 0 0; color: #e0f2fe; font-size: 14px;">Network Mapping Made Simple</p>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 32px 40px;">
                            <h2 style="margin: 0 0 16px; color: #0f172a; font-size: 20px; font-weight: 600;">You're Invited!</h2>
                            <p style="margin: 0 0 24px; color: #475569; font-size: 15px; line-height: 1.6;">
                                <strong>{invited_by_name}</strong> has invited you to join their Cartographer network map with <strong>{role_display}</strong> access.
                            </p>
                            
                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="padding: 8px 0 24px;">
                                        <a href="{invite_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #0891b2 0%, #0e7490 100%); color: #ffffff; text-decoration: none; font-size: 15px; font-weight: 600; border-radius: 8px; box-shadow: 0 2px 4px rgba(8, 145, 178, 0.3);">
                                            Accept Invitation
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 0 0 16px; color: #64748b; font-size: 13px; line-height: 1.5;">
                                This invitation will expire in <strong>{expires_hours} hours</strong>.
                            </p>
                            
                            <p style="margin: 0; color: #94a3b8; font-size: 12px; line-height: 1.5;">
                                If you didn't expect this invitation, you can safely ignore this email.
                            </p>
                            
                            <!-- Fallback link -->
                            <hr style="margin: 24px 0; border: none; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; color: #94a3b8; font-size: 11px; line-height: 1.5;">
                                If the button doesn't work, copy and paste this link into your browser:<br>
                                <a href="{invite_url}" style="color: #0891b2; word-break: break-all;">{invite_url}</a>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 40px; background-color: #f8fafc; border-radius: 0 0 12px 12px; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; color: #94a3b8; font-size: 12px; text-align: center;">
                                Cartographer - Network Mapping Tool
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    # Plain text fallback
    text_content = f"""
You're Invited to Cartographer!

{invited_by_name} has invited you to join their Cartographer network map with {role_display} access.

Click the link below to accept your invitation and create your account:
{invite_url}

This invitation will expire in {expires_hours} hours.

If you didn't expect this invitation, you can safely ignore this email.

---
Cartographer - Network Mapping Tool
"""

    try:
        params = {
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"{invited_by_name} invited you to Cartographer",
            "html": html_content,
            "text": text_content,
        }

        result = resend.Emails.send(params)
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)

        logger.info(f"Invitation email sent to {to_email} (ID: {email_id})")
        return email_id

    except Exception as e:
        logger.error(f"Failed to send invitation email to {to_email}: {e}")
        return None
