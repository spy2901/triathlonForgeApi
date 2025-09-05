import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(to_email, verification_code):
    """
    Send Verification Email

    Sends an email containing a verification code to the specified email address
    using SMTP with a styled HTML template.

    Parameters:
    ----------
    to_email : str
        The recipient's email address.
    verification_code : str
        The verification code to include in the email.

    Environment Variables:
    ----------------------
    - SMTP_SERVER : str
        The address of the SMTP server.
    - SMTP_PORT : int
        The port number of the SMTP server.
    - SMTP_USER : str
        The username for the SMTP server authentication.
    - SMTP_PASSWORD : str
        The password for the SMTP server authentication.

    Email Content:
    --------------
    - Subject: "Verify Your Registration"
    - HTML Body: Includes a verification code, styled with inline CSS.

    Returns:
    --------
    None

    Raises:
    -------
    smtplib.SMTPException:
        If an error occurs during email sending.
    EnvironmentError:
        If required environment variables are not set.

    Example:
    --------
    >>> send_email("user@example.com", "123456")

    Notes:
    ------
    - Ensure that the SMTP environment variables are configured properly.
    - This function currently uses `smtplib` for email sending and does not support
      asynchronous operations.
    """
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        raise EnvironmentError("One or more SMTP environment variables are not set.")
    subject = "Verify Your Registration"
    # Define the HTML body with the verification code
    body = f"""
    <html>
    <head>
      <title>Verify Your Registration</title>
      <style>
        body {{
          font-family: 'Arial', sans-serif;
          margin: 0;
          padding: 0;
          background-color: #e9ecef;
          text-align: center;
        }}
        .container {{
          width: 100%;
          max-width: 600px;
          margin: 20px auto;
          padding: 0;
          background-color: #ffffff;
          border-radius: 8px;
          box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
          overflow: hidden;
        }}
        .header {{
          background-color: #007bff;
          color: #ffffff;
          padding: 15px;
          border-top-left-radius: 8px;
          border-top-right-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          background-size: cover;
          background-repeat: no-repeat;
        }}
        .header img {{
          width: 50px;
          margin-right: 15px;
        }}
        .header h2 {{
          margin: 0;
          font-size: 24px;
          letter-spacing: 1px;
        }}
        .content {{
          padding: 20px;
          text-align: left;
          background-size: cover;
          background-repeat: no-repeat;
        }}
        h2 {{
          color: #333333;
          margin-top: 0;
        }}
        p {{
          color: #666666;
          line-height: 1.6;
        }}
        .code {{
          font-size: 24px;
          font-weight: bold;
          color: #ffffff;
          background-color: #dc3545;
          padding: 10px;
          border-radius: 4px;
          display: inline-block;
        }}
        .footer {{
          margin-top: 20px;
          padding: 10px;
          background-color: #007bff;
          border-bottom-left-radius: 8px;
          border-bottom-right-radius: 8px;
          font-size: 12px;
          color: #ffffff;
          text-align: center;
        }}
        .footer p {{
          margin: 0;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <img src="https://triathlonforge.com/wp-content/uploads/2025/02/triathlonForge-Logo-v1-1.png" alt="Sport Logo">
          <h2>Verify Your Registration</h2>
        </div>
        <div class="content">
          <p>Dear User,</p>
          <p>Your verification code is: <span class="code">{verification_code}</span></p>
          <p>Please enter this code to complete your registration.</p>
          <p>Best regards,<br>Triathlon Forge</p>
        </div>
        <div class="footer">
          <p>If you did not request this code, please ignore this email.</p>
        </div>
      </div>
    </body>
    </html>
    """

    # Create a multipart message
    message = MIMEMultipart()
    message['From'] = SMTP_USER
    message['To'] = to_email
    message['Subject'] = subject

    # Attach the HTML body to the email
    message.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            result = server.sendmail(SMTP_USER, to_email, message.as_string())
            server.set_debuglevel(1)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        raise  # kako bi Flask uhvatio i vratio 500 sa detaljem

