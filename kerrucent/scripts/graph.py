# -*- coding: utf-8 -*-

import os
from datetime import datetime
from enum import Enum
import rrdtool
from .constant import *

WIDTH = 1200
Duree = Enum("Duree", "h1 j1 m1 a1")
Grandeur = Enum("Grandeur", "courant tension dephasage puiss_active puiss_reactive puiss_apparente")

def safename(name) :
    return "".join(i for i in name if ord(i)<128).replace(' ', '_').replace('/', '_').replace('\\', '_')

def graph_accueil(capteur_filename, capteur_name, start='-7d', end='+0h', width=None, height=None):
    date1=datetime.now().strftime("%y%m%d%H%M%S")
    date2=datetime.now().strftime("%d/%m/%Y %Hh%M")

    capteur_filepath = os.path.join(APP_ROOT, RRD_PATH, capteur_filename+".rrd")
    graph_filepath = os.path.join(APP_ROOT, GRAPH_OUTPUT, date1+"_"+safename(capteur_name)+".png")

    if not width :
        width = WIDTH
    if not height :
        height = WIDTH/2

    width = str(int(width))
    height = str(int(height))

    params=[]
    #Le nom de l'image
    params+=[graph_filepath, "--imgformat", "PNG"]
    # Divers paramètres (cf doc)
    params+=["--force-rules-legend", "--pango-markup"]
    # La taille dde l'image (!= graphe)
    params+=["--full-size-mode", "--height", height, "--width", width]
    # Des infos HTML
    params+=["--imginfo", "<img src=\"/"+GRAPH_OUTPUT+"%s\" width=%lu height=%lu alt=\"Aperçu de "+capteur_name+"\" />"]
    # Le titre du graphe
    params+=["--title", "<span size='xx-large'>Consommation de "+capteur_name+"</span>"]
    # Les paramètres temporels du graphe
    params+=["--start", start, "--end", end]
    # Les paramètres des axes
    params+=["--vertical-label", "Puissance active (W)",
        "--right-axis", "0.01:0", "--right-axis-label", "Courant (A)"]
    # Les sources de données
    params+=["DEF:courant="+capteur_filepath+":courant:AVERAGE",
            "DEF:puiss_active="+capteur_filepath+":puiss_active:AVERAGE"]
    # Les données manipulées
    params+=["CDEF:courantx100=courant,100,*"]
    # Les fails
    params+=["CDEF:fail=courant,UN,puiss_active,UN,+,1,GE"]
    # Les variables des données
    params+=["VDEF:courant_max=courant,MAXIMUM",
            "VDEF:courant_avg=courant,AVERAGE",
            "VDEF:courant_min=courant,MINIMUM",
            "VDEF:puiss_active_max=puiss_active,MAXIMUM",
            "VDEF:puiss_active_avg=puiss_active,AVERAGE",
            "VDEF:puiss_active_min=puiss_active,MINIMUM"]
    # Affichage des échecs
    params+=["TICK:fail#FFFFa0:1.0"]
    # Légende de la légende
    params+=["COMMENT:                    ",
            "COMMENT:<b>Maximum</b>  ",
            "COMMENT:<b>Moyenne</b>  ",
            "COMMENT:<b>Minimum</b>  \l"]
    # Affichage des données et des valeurs
    params+=["AREA:puiss_active#58ACFA:Puissance active",
            "GPRINT:puiss_active_max:%6.2lf %sW",
            "GPRINT:puiss_active_avg:%6.2lf %sW",
            "GPRINT:puiss_active_min:%6.2lf %sW\\l",
           "LINE1:courantx100#FF0000:Courant         ",
            "GPRINT:courant_max:%6.2lf %sA",
            "GPRINT:courant_avg:%6.2lf %sA",
        "GPRINT:courant_min:%6.2lf %sA\\l"]
    #Affichage de la date
    params+=["TEXTALIGN:right",
           "COMMENT:"+date2]

    return rrdtool.graphv(*params)

def graph_detail(capteur_filename, capteur_name, duree, grandeurs, width=None, height=None):
    date1=datetime.now().strftime("%y%m%d%H%M%S")
    date2=datetime.now().strftime("%d/%m/%Y %Hh%M")

    capteur_filepath = os.path.join(APP_ROOT, RRD_PATH, capteur_filename+".rrd")
    graph_filepath = os.path.join(APP_ROOT, GRAPH_OUTPUT, date1+"_detail_"+safename(capteur_name)+".png")

    if not width :
        width = WIDTH
    if not height :
        height = WIDTH/2

    width = str(int(width))
    height = str(int(height))

    params=[]
    # Le nom de l'image
    params+=[graph_filepath, "--imgformat", "PNG"]
    # Divers paramètres (cf doc)
    params+=["--force-rules-legend", "--pango-markup"]
    # La taille dde l'image (!= graphe)
    params+=["--full-size-mode", "--height", height, "--width", width]
    # Des infos HTML
    params+=["--imginfo", "<img src=\"/"+GRAPH_OUTPUT+"%s\" width=%lu height=%lu alt=\"Détails de "+capteur_name+"\" />"]
    # Le titre du graphe
    params+=["--title", "<span size='xx-large'>Consommation de "+capteur_name+"</span>"]
    # Les paramètres temporels du graphe
    if duree == Duree.h1 :
        params+=["--start", "-1h"]
    elif duree == Duree.j1 :
        params+=["--start", "-1d"]
    elif duree == Duree.m1 :
        params+=["--start", "-1mon"]
    elif duree == Duree.a1 :
        params+=["--start", "-1y"]
    # Les paramètres des axes
    y_axis_param=""
    size = 0
    if Grandeur.courant in grandeurs :
        y_axis_param+="Courant x100 (A)\n"
        size+=1
    if Grandeur.tension in grandeurs :
        y_axis_param+="Tension x10 (V)\n"
        size+=1
    if Grandeur.puiss_active in grandeurs :
        y_axis_param+="Puissance Active (W)\n"
        size+=1
    if Grandeur.puiss_reactive in grandeurs :
        y_axis_param+="Puissance Réactive (VAR)\n"
        size+=1
    if Grandeur.puiss_apparente in grandeurs :
        y_axis_param+="Puissance Apparente (VA)\n"
        size+=1
    y_axis_param = y_axis_param[:-2]
    params+=["--vertical-label", y_axis_param]
    if Grandeur.dephasage in grandeurs :
        params+=["--right-axis", "0.1:0",
            "--right-axis-label", "Déphasage (°)"]
        size+=1
    # Les sources de données
    if Grandeur.courant in grandeurs :
        params+=["DEF:courant="+capteur_filepath+":courant:AVERAGE"]
        if size == 1 :
            params+=["DEF:courant_pred="+capteur_filepath+":courant:HWPREDICT",
                    "DEF:courant_dev="+capteur_filepath+":courant:DEVPREDICT"]
    if Grandeur.tension in grandeurs :
        params+=["DEF:tension="+capteur_filepath+":tension:AVERAGE"]
        if size == 1 :
            params+=["DEF:tension_pred="+capteur_filepath+":tension:HWPREDICT",
                    "DEF:tension_dev="+capteur_filepath+":tension:DEVPREDICT"]
    if Grandeur.dephasage in grandeurs :
        params+=["DEF:dephasage="+capteur_filepath+":dephasage:AVERAGE"]
        if size == 1 :
            params+=["DEF:dephasage_pred="+capteur_filepath+":dephasage:HWPREDICT",
                    "DEF:dephasage_dev="+capteur_filepath+":dephasage:DEVPREDICT"]
    if Grandeur.puiss_active in grandeurs :
        params+=["DEF:active="+capteur_filepath+":puiss_active:AVERAGE"]
        if size == 1 :
            params+=["DEF:pred="+capteur_filepath+":puiss_active:HWPREDICT",
                    "DEF:dev="+capteur_filepath+":puiss_active:DEVPREDICT"]
    if Grandeur.puiss_reactive in grandeurs :
        params+=["DEF:reactive="+capteur_filepath+":puiss_reactive:AVERAGE"]
        if size == 1 :
            params+=["DEF:pred="+capteur_filepath+":puiss_reactive:HWPREDICT",
                    "DEF:dev="+capteur_filepath+":puiss_reactive:DEVPREDICT"]
    if Grandeur.puiss_apparente in grandeurs :
        params+=["DEF:apparente="+capteur_filepath+":puiss_apparente:AVERAGE"]
        if size == 1 :
            params+=["DEF:pred="+capteur_filepath+":puiss_apparente:HWPREDICT",
                    "DEF:dev="+capteur_filepath+":puiss_apparente:DEVPREDICT"]
    # Les données manipulées
    if Grandeur.courant in grandeurs :
        params+=["CDEF:courantx100=courant,100,*"]
        if size == 1 :
            params+=["CDEF:pred=courant_pred,100,*",
                    "CDEF:dev=courant_dev,100,*"]
    if Grandeur.tension in grandeurs :
        params+=["CDEF:tensionx10=tension,10,*"]
        if size == 1 :
            params+=["CDEF:pred=tension_pred,10,*",
                    "CDEF:dev=tension_dev,10,*"]
    if Grandeur.dephasage in grandeurs :
        params+=["CDEF:dephasagex10=dephasage,10,*"]
        if size == 1 :
            params+=["CDEF:pred=dephasage_pred,10,*",
                    "CDEF:dev=dephasage_dev,10,*"]
    if size == 1 :
        params+=["CDEF:lower=pred,dev,2,*,-", "CDEF:upper=pred,dev,2,*,+"]
    # Les fails
    fail_param=""
    if Grandeur.courant in grandeurs :
        fail_param+=",courant,UN"
    if Grandeur.tension in grandeurs :
        fail_param+=",tension,UN"
    if Grandeur.dephasage in grandeurs :
        fail_param+=",dephasage,UN"
    if Grandeur.puiss_active in grandeurs :
        fail_param+=",active,UN"
    if Grandeur.puiss_reactive in grandeurs :
        fail_param+=",reactive,UN"
    if Grandeur.puiss_apparente in grandeurs :
        fail_param+=",apparente,UN"
    if size > 0 :
        fail_param=fail_param[1:]+",+"*(size-1)+",1,GE"
        params+=["CDEF:fail="+fail_param]
    # Les variables des données
    if Grandeur.courant in grandeurs :
        params+=["VDEF:courant_max=courant,MAXIMUM",
               "VDEF:courant_avg=courant,AVERAGE",
                "VDEF:courant_min=courant,MINIMUM"]
    if Grandeur.tension in grandeurs :
        params+=["VDEF:tension_max=tension,MAXIMUM",
                "VDEF:tension_avg=tension,AVERAGE",
                "VDEF:tension_min=tension,MINIMUM"]
    if Grandeur.dephasage in grandeurs :
        params+=["VDEF:dephasage_max=dephasage,MAXIMUM",
               "VDEF:dephasage_avg=dephasage,AVERAGE",
                "VDEF:dephasage_min=dephasage,MINIMUM"]
    if Grandeur.puiss_active in grandeurs :
        params+=["VDEF:active_max=active,MAXIMUM",
                "VDEF:active_avg=active,AVERAGE",
                "VDEF:active_min=active,MINIMUM"]
    if Grandeur.puiss_reactive in grandeurs :
        params+=["VDEF:reactive_max=reactive,MAXIMUM",
               "VDEF:reactive_avg=reactive,AVERAGE",
                "VDEF:reactive_min=reactive,MINIMUM"]
    if Grandeur.puiss_apparente in grandeurs :
        params+=["VDEF:apparente_max=apparente,MAXIMUM",
                "VDEF:apparente_avg=apparente,AVERAGE",
                "VDEF:apparente_min=apparente,MINIMUM"]
    # Affichage des échecs
    params+=["TICK:fail#FFFFa0:1.0"]
    # Légende de la légende
    params+=["COMMENT:                       ",
            "COMMENT:<b>Maximum</b>    ",
            "COMMENT:<b>Moyenne</b>    ",
            "COMMENT:<b>Minimum</b>    \\l"]
    # Affichage des données et des valeurs
    if Grandeur.courant in grandeurs :
        params+=["LINE1:courantx100#FF0000:Courant            ",
                "GPRINT:courant_max:%6.2lf %sA  ",
                "GPRINT:courant_avg:%6.2lf %sA  ",
                "GPRINT:courant_min:%6.2lf %sA  \\l"]
    if Grandeur.tension in grandeurs :
        params+=["LINE1:tensionx10#00FF00:Tension            ",
                "GPRINT:tension_max:%6.2lf %sV  ",
                "GPRINT:tension_avg:%6.2lf %sV  ",
                "GPRINT:tension_min:%6.2lf %sV  \\l"]
    if Grandeur.dephasage in grandeurs :
        params+=["LINE1:dephasagex10#0000FF:Déphasage          ",
                "GPRINT:dephasage_max:%6.2lf  °  ",
                "GPRINT:dephasage_avg:%6.2lf  °  ",
                "GPRINT:dephasage_min:%6.2lf  °  \\l"]
    if Grandeur.puiss_active in grandeurs :
        params+=["LINE1:active#FFBF00:Puissance Active   ",
                "GPRINT:active_max:%6.2lf %sW  ",
                "GPRINT:active_avg:%6.2lf %sw  ",
                "GPRINT:active_min:%6.2lf %sW  \\l"]
    if Grandeur.puiss_reactive in grandeurs :
        params+=["LINE1:reactive#2E9AFE:Puissance Réactive ",
                "GPRINT:reactive_max:%6.2lf %sVAR",
                "GPRINT:reactive_avg:%6.2lf %sVAR",
                "GPRINT:reactive_min:%6.2lf %sVAR\\l"]
    if Grandeur.puiss_apparente in grandeurs :
        params+=["LINE1:apparente#FF00FF:Puissance Apparente",
                "GPRINT:apparente_max:%6.2lf %sVA ",
                "GPRINT:apparente_avg:%6.2lf %sVA ",
                "GPRINT:apparente_min:%6.2lf %sVA \\l"]
    if size == 1 :
        params+=["LINE1:lower#000000",
                "LINE1:pred#000000",
                "LINE1:upper#000000"]
    # Affichage de la date
    params+=["TEXTALIGN:right",
           "COMMENT:"+date2 ]

    return rrdtool.graphv(*params)

if __name__=="__main__":
    print( graph_detail("test", "Frigo",Duree.j1,[Grandeur.tension])["image_info"] )
