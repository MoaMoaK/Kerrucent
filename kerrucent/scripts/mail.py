import smtplib
from email.mime.text import MIMEText

me = "alertes-kerrucent@gmail.com (Alertes Kerrucent)"
you = "kervella.mael@gmail.com"

msg=MIMEText("test en python 1")
msg['From'] = me
msg['To'] = you
msg['Subject'] = 'Alertes kerrucent en python'

s = smtplib.SMTP('localhost')
s.sendmail(me, [you], msg.as_string())
s.quit()

