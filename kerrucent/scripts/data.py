#!/bin/usr/python

import socket
from .constant import *

# On ouvre un socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (SERVER_IP, SERVER_PORT)
sock.bind(server_address)

def listen() :
    """Ecoute le socket et renvoie les données reçue pour peu
    qu'elles correspondent à des données cohérentes"""

    # On attend un paquet
    data, address = sock.recvfrom(1024)

    # On reforme les données
    d = data.decode('utf-8').replace('\x00', '').split('/')

    # On sépare les infos les unes des autres
    ident = d[0]
    values = ['U']*6
    for i in range(len(values)) :
        try :
            values[i] = d[i+1] if MINIMA[i] <= float(d[i+1]) <= MAXIMA[i] else 'U'
        except :
            pass

    # On renvoie les infos utiles
    return ident, values
