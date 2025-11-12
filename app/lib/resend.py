from urllib.parse import quote_plus
import resend

from app.core.config import settings


resend.api_key = settings.resend_api_key


def send_reset_link(to_email: str, token: str):
	frontend_url = f"{settings.frontend_url.rstrip('/')}/{settings.frontend_password_reset_path}?token={quote_plus(token)}"
	try:
		html_body = f"""
<!doctype html>
<html>
  <body>
    <p>Hi,</p>
    <p>You (or someone using this email) requested a password reset for your account.
       Click the button below to reset your password. This link will expire soon.</p>

    <p style="text-align:center; margin: 24px 0;">
      <a href="{frontend_url}" target="_blank" rel="noopener noreferrer"
         style="display:inline-block; padding:14px 22px; border-radius:8px; text-decoration:none;
                font-weight:600; font-size:16px; background-color:#0b74ff; color:#ffffff;">
        Reset your password
      </a>
    </p>

    <p>If the button doesn't work, copy and paste this URL into your browser:</p>
    <p><a href="{frontend_url}" target="_blank" rel="noopener noreferrer">{frontend_url}</a></p>

    <hr>
    <p style="font-size:12px; color:#666">If you did not request a password reset, you can safely ignore this email.</p>
  </body>
</html>
"""
		text_body = f"""
Hi,

You requested a password reset for your account.
Open this link to reset your password (expires soon):

{frontend_url}

If you did not request this, ignore this email.
"""
		
		params = {
			"from": settings.resend_from_address,
			"to": [to_email],
			"subject": "Reset your password",
			"html": html_body,
			"text": text_body, 
		}
		resend.Emails.send(params)
	except Exception as e:
		print("Error sending password reset email with Resend:", e)

