# -*- coding: utf-8 -*-

import rrdtool
import random
import time
import os
from math import sin, pi
from .constant import *

def create_rrd(name, start=None, alpha=0.000192522, beta=0.00000802250, period=86400) :
    """Crée une base de donnée rrd avec des paramètres adaptés aux capteurs"""

    if not start :
        start = int(time.time())

    params = []

    # Le nom du fichier
    params += [os.path.join(APP_ROOT, RRD_PATH, name+'.rrd')]
    # Les paramètres temporels
    params += ['--start', str(start), '--step', '1']
    # Les Data Sources DS:<name>:<source_type>:<heartbeat>:<min>:<max>
    # Les 6 grandeurs qui stockent une valeur par seconde
    params += ['DS:courant:GAUGE:1:0:30',
            'DS:tension:GAUGE:1:0:300',
            'DS:dephasage:GAUGE:1:0:360',
            'DS:puiss_active:GAUGE:1:0:10000',
            'DS:puiss_reactive:GAUGE:1:0:10000',
            'DS:puiss_apparente:GAUGE:1:0:10000']
    # Les Round Robin Archives standard RRA:<aggregation_type>:<percentage_for_unknwon>:<steps>:<row>
    # On garde une valeur par seconde pendant 10 jours
    #          une valeur par minute pendant 90 jours
    #          une valeur par heure pendant 18 mois
    #          une valeur par jour pendant 10 ans
    params += ['RRA:AVERAGE:0.5:1:864000',
            'RRA:AVERAGE:0.5:60:129600',
            'RRA:AVERAGE:0.5:3600:13392',
            'RRA:AVERAGE:0.5:86400:3660']
    # Les Round Robin Archives de prédiction RRA:HWPREDICT:<rows>:<alpha>:<beta>:<seasonal_period>
    # Crée automatiquement RRA:HWPREDICT, RRA:SEASONAL, RRA:DEVPREDICT, RRA:DEVSEASONAL, RRA:FAILURES
    params += ['RRA:HWPREDICT:864000:'+str(alpha)+':'+str(beta)+':'+str(period)]

    return rrdtool.create(*params)



def del_rrd(name):
    """Supprime une RRD"""

    os.remove(os.path.join(APP_ROOT, RRD_PATH, name+'.rrd'))

    return None



def update_rrd(name, values, time=None) :
    """Ajoute une valeur dans une rrd"""

    if not time :
        time = int(time.time())

    params = []
    # Le nom de la RRD
    params += [os.path.join(APP_ROOT, RRD_PATH, name+'.rrd')]
    # Les valeurs de la RRD
    val = ':'.join(str(v) for v in values)
    params += [str(time)+':'+val]

    return rrdtool.update(*params)



def tune_rrd_pred(name, alpha=None, beta=None) :
    """Permet de modfiier les paramètres alpha et beta des RRD et de prédiction"""

    if alpha :
        rrdtool.tune(os.path.join(APP_ROOT, RRD_PATH, name+'.rrd'), '--alpha', str(alpha))
    if beta :
        rrdtool.tune(os.path.join(APP_ROOT, RRD_PATH, name+'.rrd'), '--beta', str(beta))
    return None



def has_error (name, start='-1min') :
    """Vérifie si une rrd (donc un capteur présente des erreurs"""

    timerange, names, results = rrdtool.fetch(os.path.join(APP_ROOT, RRD_PATH, name+'.rrd'), 'FAILURES', '--start', start)
    for i in range(len(results)) :
        for j in range(len(names)) :
            if results[i][j] == 1.0 :
                return (i,j)

    return None






