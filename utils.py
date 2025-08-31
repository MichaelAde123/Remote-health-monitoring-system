import smtplib
from email.message import EmailMessage

def send_email(recipient, subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = 'your_email@example.com'
    msg['To'] = recipient

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('your_email@example.com', 'your_app_password')
            server.send_message(msg)
            print("Email sent successfully.")
    except Exception as e:
        print("Failed to send email:", e)