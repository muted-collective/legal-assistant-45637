from dotenv import find_dotenv, load_dotenv
from os.path import basename
import time

import re
import json
import os
import smtplib, ssl
from typing_extensions import override
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
from email.mime.application import MIMEApplication
from email.utils import formataddr
load_dotenv()



def send_email(To, CC, BCC, Subject, Body, Attachments): 

    email_to= To.split(',')
    email_to_cc= CC.split(',')
    email_to_bcc= BCC.split(',')
    email_to_subject= Subject
    email_to_body= f""" {Body} """

    email_sender= os.getenv('EMAIL_SENDER')
    email_password= os.getenv('EMAIL_PASSWORD')

    if not email_password:
        raise ValueError('EMAIL_PASSWORD environment variable not set')

    all_recipients= email_to + email_to_cc + email_to_bcc

    msg= MIMEMultipart()
    msg['From']= formataddr(("Andile Vilakazi", f"{email_sender}"))
    msg['To']= ", ".join(email_to)
    msg['Cc']= ", ".join(email_to_cc)
    msg['Bcc']= ", ".join(email_to_bcc)
    msg['Subject']= email_to_subject


    # Attach body text
    part_1= MIMEText(email_to_body, "plain")   
    msg.attach(part_1)


    smtp_server= 'smtp.bindaattorneys.co.za'
    smtp_port= 25
    context= ssl.create_default_context()

    try:

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(email_sender, email_password)
            server.sendmail(from_addr= email_sender, to_addrs= all_recipients, msg= msg.as_string())
            success_message= f'Email succesfully sent to {all_recipients}'

    except Exception as e:
        success_message= f'Failure to send email: {e}'

    print(success_message)

    return success_message


recipient= 'dkdrabile@gmail.com'
subject= 'Test'
Body= 'Hello World Tests'


send_email(To= recipient, Subject= subject, Body=Body, CC= '', BCC='', Attachments='')
