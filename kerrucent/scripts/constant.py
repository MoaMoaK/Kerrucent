# -*- coding: utf-8 -*-

# L'emplacement de Kerrucent
APP_ROOT = "/home/pi/kerrucent/kerrucent/"
# Le dossier contenant les RRD
RRD_PATH = "rrd/"
# Le dossier contenant les graph générés
GRAPH_OUTPUT = "static/graph/"

# Les maximas et minimas des valeurs attendues
MAXIMA = [30, 300, 360, 10000, 10000, 10000]
MINIMA = [0, 0, 0, 0, 0, 0]

# L'IP du server pour les capteurs
SERVER_IP = '10.2.6.155'
# Le port d'écoute du serveur pour les capteurs
SERVER_PORT = 5005
