import smtplib
import time
from email.mime.text import MIMEText
from .rrd import has_error

FROM = "alertes-kerrucent@gmail.com (Alertes Kerrucent)"

def sendmail (to, text=None) :
    """Envoie un email d'alerte à une adresse mail spécifique. Text personalisé optionnel"""

    if not text :
        text = "Une erreur a été détectée sur un des capteurs surveillés par kerrucent. Vous pouvez en apprendre plus sur\n:http://kerrucent.rez"

    msg=MIMEText(text)
    msg['From'] = FROM
    msg['To'] = to
    msg['Subject'] = '[Kerrucent] Détection d\'erreur'

    s = smtplib.SMTP('localhost')
    s.sendmail(FROM, [to], msg.as_string())
    s.quit()

    return None

