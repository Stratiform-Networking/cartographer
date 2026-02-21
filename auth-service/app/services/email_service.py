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
    to_email: str, invite_token: str, invited_by_name: str, role: str, expires_hours: int = 72
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
    role_display = {"member": "Member", "admin": "Admin"}.get(role, role)

    # HTML email template
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You're Invited to Cartographer</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 0; font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #0f172a;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #0f172a;">
        <tr>
            <td style="padding: 48px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 580px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 40px 40px 32px; text-align: center; background: linear-gradient(135deg, #0fb685 0%, #0994ae 100%); border-radius: 16px 16px 0 0;">
                            <div style="width: 56px; height: 56px; background: rgba(255, 255, 255, 0.2); border-radius: 14px; margin: 0 auto 16px; text-align: center; line-height: 56px; font-size: 28px;">🗺️</div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: 700; letter-spacing: -0.5px;">Cartographer</h1>
                            <p style="margin: 10px 0 0; color: rgba(255, 255, 255, 0.9); font-size: 15px; font-weight: 500;">Network Mapping Made Simple</p>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 40px 40px 36px;">
                            <h2 style="margin: 0 0 16px; color: #0f172a; font-size: 24px; font-weight: 600; letter-spacing: -0.3px; text-align: center;">You're Invited!</h2>
                            <p style="margin: 0 0 32px; color: #475569; font-size: 16px; line-height: 1.7; text-align: center;">
                                <strong style="color: #0f172a;">{invited_by_name}</strong> has invited you to join their Cartographer network map with <strong style="color: #0f172a;">{role_display}</strong> access.
                            </p>

                            <!-- CTA Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="padding: 8px 0 32px; text-align: center;">
                                        <a href="{invite_url}" style="display: inline-block; padding: 16px 40px; background: linear-gradient(135deg, #06b6d4 0%, #2563eb 100%); color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 600; border-radius: 12px; box-shadow: 0 4px 14px rgba(6, 182, 212, 0.35);">
                                            Accept Invitation →
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <!-- Expiry notice -->
                            <div style="background-color: #f8fafc; padding: 16px 20px; border-radius: 12px; margin: 0 0 20px; border: 1px solid #e2e8f0; text-align: center;">
                                <p style="margin: 0; color: #64748b; font-size: 14px; line-height: 1.5;">
                                    ⏰ This invitation will expire in <strong style="color: #0f172a;">{expires_hours} hours</strong>
                                </p>
                            </div>

                            <p style="margin: 0; color: #94a3b8; font-size: 13px; line-height: 1.5; text-align: center;">
                                If you didn't expect this invitation, you can safely ignore this email.
                            </p>

                            <!-- Fallback link -->
                            <hr style="margin: 28px 0; border: none; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; color: #94a3b8; font-size: 12px; line-height: 1.6; text-align: center;">
                                If the button doesn't work, copy and paste this link:<br>
                                <a href="{invite_url}" style="color: #0994ae; word-break: break-all; font-weight: 500;">{invite_url}</a>
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 40px 28px; background-color: #f8fafc; border-radius: 0 0 16px 16px; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0; color: #64748b; font-size: 13px; text-align: center; font-weight: 500;">
                                Cartographer - Network Mapping Tool
                            </p>
                        </td>
                    </tr>
                </table>

                <!-- Bottom branding -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 580px; margin: 24px auto 0;">
                    <tr>
                        <td style="text-align: center;">
                            <p style="margin: 0; color: #475569; font-size: 12px;">
                                Powered by <span style="color: #0fb685; font-weight: 600;">Cartographer</span>
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


def send_password_reset_email(
    to_email: str,
    reset_token: str,
    expires_minutes: int = 60,
) -> str | None:
    """
    Send a password reset email.

    Returns the email ID if successful, None if failed or not configured.
    """
    if not is_email_configured():
        logger.warning(f"Email not configured - password reset email for {to_email} not sent")
        return None

    resend = _get_resend()
    if not resend:
        return None

    reset_url = f"{settings.application_url}/reset-password?token={reset_token}"

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset your Cartographer password</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0f172a; padding: 40px 16px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 560px; background: #ffffff; border-radius: 14px; overflow: hidden;">
                    <tr>
                        <td style="padding: 28px 28px 20px; background: linear-gradient(135deg, #0fb685 0%, #0994ae 100%); color: #ffffff;">
                            <h1 style="margin: 0; font-size: 24px;">Cartographer</h1>
                            <p style="margin: 8px 0 0; opacity: 0.92;">Password reset request</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 28px;">
                            <p style="margin: 0 0 14px; color: #0f172a; font-size: 16px;">
                                We received a request to reset your password.
                            </p>
                            <p style="margin: 0 0 20px; color: #334155; font-size: 14px; line-height: 1.6;">
                                Click the button below to choose a new password. This link expires in <strong>{expires_minutes} minutes</strong>.
                            </p>
                            <p style="margin: 0 0 18px;">
                                <a href="{reset_url}" style="display: inline-block; padding: 12px 24px; border-radius: 10px; text-decoration: none; color: #ffffff; background: linear-gradient(135deg, #06b6d4 0%, #2563eb 100%); font-weight: 600;">
                                    Reset Password
                                </a>
                            </p>
                            <p style="margin: 0 0 10px; color: #64748b; font-size: 12px; line-height: 1.5;">
                                If you did not request this, you can ignore this email.
                            </p>
                            <p style="margin: 0; color: #94a3b8; font-size: 12px; word-break: break-all;">
                                {reset_url}
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

    text_content = f"""
Reset your Cartographer password

We received a request to reset your password.
Use the link below to set a new password (expires in {expires_minutes} minutes):
{reset_url}

If you did not request this, you can ignore this email.
"""

    try:
        params = {
            "from": settings.email_from,
            "to": [to_email],
            "subject": "Reset your Cartographer password",
            "html": html_content,
            "text": text_content,
        }

        result = resend.Emails.send(params)
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        logger.info(f"Password reset email sent to {to_email} (ID: {email_id})")
        return email_id
    except Exception as e:
        logger.error(f"Failed to send password reset email to {to_email}: {e}")
        return None
