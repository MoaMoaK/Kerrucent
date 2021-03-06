# -*- coding: utf-8 -*-




#############
## Imports ##
#############

# Import PyPI packages
import os
import sys
import sqlite3
import re
import time
from random import randint
from hashlib import sha256
import threading

# Import other packages
from email_validator import validate_email, EmailNotValidError

# Import flask packages
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash

# Import custom packages
from .scripts.graph import *
from .scripts.rrd import *
from .scripts.mail import *
from .scripts.data import *




#############################
## Initialisation de flask ##
#############################

app = Flask(__name__) # create the application instance :)
app.config.from_object(__name__) # load config from this file , kerrucent.py

# Load default config and override config from an environment variable
app.config.update(dict(
    DBSCHEMA=os.path.join(app.root_path, 'db/', 'schema.sql'),
    DATABASE=os.path.join(app.root_path, 'db/', 'kerrucent.db'),
    SECRET_KEY='development key',
))
app.config.from_envvar('KERRUCENT_SETTINGS', silent=True)





#################################################
## Fonction de connection à la base de données ##
##  inspiré du tutoriel de Flask               ##
#################################################

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
    db = get_db()
    with app.open_resource(app.config['DBSCHEMA'], mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command()
def initdb():
    """Initializes the database."""
    init_db()
    log('Initialized the database.')

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()




#################################
## Détection d'erreur (thread) ##
#################################

def test_error () :
    """Vérifie régulièrement si il y a une erreur pour chaque capteur surveillé et envoie un mail si il y a une erreur"""

    # On doit ramener le contexte de l'appli
    # car on lance la requete BDD avant la 1ère requete HTTP
    with app.app_context():

        # On récupère les infos sur les catpeurs à surveiller (id, filename et email)
        db = get_db()
        cur = db.execute('SELECT probes.name, probes.filename, probes.id, alerts.email FROM alerts JOIN probes ON alerts.probe_id=probes.id')
        probes_to_watch = cur.fetchall()

        # On trie la liste des capteurs pour éviter de checker 2 fois le même capteur pour 2 emails
        sorted_probes = unique (probes_to_watch)

        # Pour chaque capteur, on vérifie si il y a des erreurs et on envoie un mail le cas échéant
        for p in sorted_probes :
            if has_error(p[0]['filename']) :
                for j in range(len(p)) :
                    sendmail(p[j]['email'], text='Le capteur '+p[j]['name']+' a des erreurs')
                    log('Email envoyé à '+p[j]['email']+' pour une erreur sur le capteur '+p[j]['name'])

        # On met le thread en puase pour pas spammer de mails et de vérifictions
        time.sleep(60)




def unique (s) :
    """Trie les tuples (name, filename, id, email) pour éviter les doublons de capteurs (sans perdre l'info de l'email)"""

    # On utilise un tri par dictionnaire (c'est globalement ce qu'il y a de plus rapide en python)
    u = {}

    # On regarde tous les éléments
    for x in s :
        # Si on a jamais rencontré ce capteur, on crée le champs associé dans le dico
        if not x['name'] in u.keys() :
            u[x['name']] = []
        # On ajoute le cpateur (et les infos associées) à ce champs
        u[x['name']] += [x]

    # On renvoie les tuples d'infos
    return u.values()




# On lance un thread pour la vérification d'erreur et l'envoi d'email
threading.Thread(target=test_error).start()




####################################################
## Récupération des données des capteurs (thread) ##
####################################################

def get_data() :
    """Récupère en permanance les données sur le réseau
    et rafraichit les données de la BDD toutes les 15 min environ
    pour ne pas faire des requetes BDD ultra fréquentes"""

    while (1) :
        # On doit ramener le contexte de l'appli
        # car on lance la requete BDD avant la 1ère requete HTTP
        with app.app_context():

            # On récupère les infos sur les capteurs à remplir (filename et mac)
            db = get_db()
            cur = db.execute('SELECT probes.filename, probes.mac FROM probes')
            probes_info = cur.fetchall()
            probes_dict = make_dict(probes_info)

        log('Cache des capteurs à remplir mis à jour')

        # On déclenche pendant 15 minutes environ
        # (sous hypothèse d'une donnée dispo en permanance
        # et tous les capteurs envoie des données)
        for i in range(60*15*len(probes_dict.keys())) :
            ident, values = listen()
            if ident in probes_dict.keys() :
                update_rrd(probes_dict[ident], values)
            time.sleep(1)



def make_dict(data) :
    """Transforme le résultat de la requete BDD en dictionnaire {identifiant : filename}"""

    res = {}
    for d in data :
        res[d['mac']] = d['filename']

    return res



# On lance un thread pour l'écoute des données
threading.Thread(target=get_data).start()




#############################
## Autres fonctions utiles ##
#############################

def saltpassword (password, salt) :
    """Retourne un mot de passé salé selon l'algo sha256(pass+salt)"""

    saltedpassword = password + str(salt)
    return sha256(saltedpassword.encode('utf-8')).hexdigest()



def log (message) :
    """Print un message pour qu'il apparaisse dans les logs"""

    print(time.ctime() + ' [INFO] ' + message)
    return None



###########################
## Flask views : acceuil ##
###########################

@app.route('/')
def accueil() :
    """La page d'acceuil du site (pas très utile mais pourra être utile un jour"""

    return render_template('accueil.html')




#################################
## Flask views : visualisation ##
#################################

@app.route('/apercu/')
def apercu() :
    """La page web qui donne un aperçu de l'ensemble des capteurs gérés par le système"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # On récupères les infos sur les capteurs
    db = get_db()
    cur = db.execute('SELECT id, name, filename FROM probes ORDER BY id')
    probes = cur.fetchall()

    # On génère les images pour chacun de ces capteurs
    images = {}
    for p in probes :
        images[p['id']] = graph_accueil(p['filename'], p['name'], width=550, height=300)['image_info']

    # On renvoie l'HTML avec les infos
    return render_template('apercu.html', probes=probes, images=images)




@app.route('/detail/<int:id>/', methods=['GET', 'POST'])
def detail(id) :
    """La page web qui permet d'avoir le détail de consommation d'un capteur en particulier"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # On récupère les infos sur le capteur demandé
    db = get_db()
    cur = db.execute('SELECT id, name, filename, mac FROM probes WHERE id=?', [id])
    probe = cur.fetchone()

    # On vérifie que l'id correspond bien à un capteur
    if not probe :
        flash ('Le capteur que vous avez demandé n\'existe pas')
        return redirect(url_for('apercu'))

    # Valeur par défaut des paramètres
    time = Duree.j1
    grandeurs = []

    # Si l'utilisateur demande des valeurs de paramètres en particulier
    if request.method == 'POST' :

        # On récupère la durée de visualisation demandée
        try :
            if request.form['time'] == 'heure':
                time = Duree.h1
            elif request.form['time'] == 'jour':
                time = Duree.j1
            elif request.form['time'] == 'mois':
                time = Duree.m1
            elif request.form['time'] == 'an':
                time = Duree.a1
        except :
            pass

        # On récupère la ou les grandeurs demandées
        if 'courant' in request.form.getlist('grandeurs'):
            grandeurs.append(Grandeur.courant)
        if 'tension' in request.form.getlist('grandeurs'):
            grandeurs.append(Grandeur.tension)
        if 'dephasage' in request.form.getlist('grandeurs'):
            grandeurs.append(Grandeur.dephasage)
        if 'puiss_active' in request.form.getlist('grandeurs'):
            grandeurs.append(Grandeur.puiss_active)
        if 'puiss_reactive' in request.form.getlist('grandeurs'):
            grandeurs.append(Grandeur.puiss_reactive)
        if 'puiss_apparente' in request.form.getlist('grandeurs'):
            grandeurs.append(Grandeur.puiss_apparente)

    # Si aucune grandeur demandé ou methode GET => on met au moins une
    # grandeur a visualiser pour éviter un graph vide et inutile
    if len(grandeurs) == 0 :
        grandeurs.append(Grandeur.courant)

    # On génère l'image avec les paramètres ainsi choisi
    image = graph_detail(probe['filename'], probe['name'], time, grandeurs, width=1000, height=500)['image_info']

    # On renvoie l'HTML avec les infos
    return render_template('detail.html', probe=probe, image=image)




#########################
## Flask views : users ##
#########################

@app.route('/manageusers/')
def manage_users():
    """La page qui permet de gérer les utilisateur (modification, ajout et suppression)"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # On récupère la liste de tous les utilisateurs
    db = get_db()
    cur = db.execute('SELECT id, username FROM users ORDER BY id')
    users = cur.fetchall()

    # On renvoie l'HTML avec toutes les infos
    return render_template('manageusers.html', users=users)




@app.route('/removeuser/<int:id>/')
def remove_user(id):
    """La page pour retirer un utilisateur en particulier"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # On récupères des infos sur l'utilisateur en question
    db = get_db()
    cur = db.execute('SELECT username FROM users WHERE id=?', [id])
    user = cur.fetchone()

    # On vérifie que l'id correspond bien à un utilisateur
    if not user :
        flash('L\'utilisateur n\'a pas été trouvé')
    else :
        # On supprime l'utilisateur en question de la BDD
        try :
            db.execute('DELETE FROM users WHERE id=?', [id])
            db.commit()
        except :
            flash ('Une erreur est survenue lors de la suppression de '+user['username']+' de la BDD')
        else :
            log('Utilisateur '+user['username']+' supprimé')
            flash('L\'utilisateur '+user['username']+' a bien été supprimé')

    # On revient sur la gestion des utilisateurs (pas besoin de page web dédiée)
    return redirect(url_for('manage_users'))




@app.route('/edituser/<int:id>/', methods=['GET', 'POST'])
def edit_user(id):
    """La page web qui permet de modifier les paramètres d'un utilisateur en particulier"""

    if not session.get('logged_in') :
        return redirect(url_for('login'))

    # Les erreurs qu'on remonte à l'utilisateur (si il y en a)
    error_name = None
    error_pass = None

    # On récupère des infos sur l'utilisateur en particulier
    db = get_db()
    cur = db.execute('SELECT id, username FROM users WHERE id=?', [id])
    user = cur.fetchone()

    # On vérifie que l'utilisateur existe
    if not user:
        flash('L\'utilisateur que vous avez demandé n\'existe pas')
        return redirect(url_for('manage_users'))

    # Si une modifiaction est demandée
    if request.method == 'POST':
        # Demande de modification du nom d'utilisateur
        if request.form['username'] and request.form['username'] != user['username']:
            username = request.form['username']
            # On essaye dechanger le nom
            try :
                db.execute('UPDATE users SET username=? WHERE id=?',
                        [username, id])
                db.commit()
            except :
                error_name = 'Une erreur est survenue lors de la modification du nom d\'utilisateur dans la base de donnée'
                print(sys.exc_info())
            else:
                log('Nom de '+user['username']+' changé en '+username)
                flash ('Le nom d\'utilisateur de '+user['username']+' a bien été changé en '+username)


        #Demande de changement de mot de passe
        if request.form['password1'] or request.form['password2'] :
            if not request.form['password1'] or not request.form['password2'] :
                # Il manque un des deux champs 'password'
                error_pass = 'Veuillez compléter les deux champs'
            elif request.form['password1'] != request.form['password2'] :
                # Les deux champs 'password' ne correspondent pas
                error_pass = 'Les deux mot de passe ne correspondent pas'
            else :
                # Tout va bien on récupère le mot de passe et un salt
                password = request.form['password1']
                salt = randint(1000000, 1000000000)
                # On essaye de modifier la BDD avec ces nouveaux identifiants
                try :
                    db.execute('UPDATE users SET password=?, salt=? WHERE id=?',
                            [saltpassword(password, salt), salt, id])
                    db.commit()
                except :
                    error_pass = 'Une erreur est survenue lors de la modification du mot de passe dans la base de donnée'
                    print(sys.exc_info())
                else :
                    log('Mot de passe de '+user['username']+' changé')
                    flash('Le mot de passe de '+user['username']+' a correctement été modifié')

    # On recharge les modifications depuis la BDD pour prendre en compte les modif effectuées
    # Nécessaire pour un affichage joli et sans ambiguité
    user = db.execute('SELECT id, username FROM users WHERE id=?', [id]).fetchone()

    # On renvoie l'HTML avec les infos
    return render_template('edituser.html', user=user, error_name=error_name, error_pass=error_pass)




@app.route('/adduser/', methods=['GET', 'POST'])
def add_user():
    """La page web qui permet d'ajouter un utilisateur"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Les erreurs qu'on remonte à l'utilisateur (si il y en a)
    error = None

    # Si les données ont été envoyées
    if request.method == 'POST' :

        if not request.form['username'] or not request.form['password1'] or not request.form['password2'] :
            # Si il manque un champs
            error = 'Les champs ne sont pas tous remplis'
        elif request.form['password1'] != request.form['password2'] :
            # Si les deux mdp ne correpondent pas
            error = 'Les deux mot de passe ne correspondent pas'
        else :
            # On récupères les infos à mettre à jour
            username = request.form['username']
            password = request.form['password1']
            salt = randint(1000000, 1000000000)

            # On essaye d'ajouter l'utilisateur
            try :
                db = get_db()
                db.execute('INSERT INTO users (username, password, salt) VALUES (?, ?, ?)',
                            [username, saltpassword(password, salt), salt])
                db.commit()
            except :
                error = 'Une erreur est survenue lors de l\'ajout de l\'utilisateur à la base de données'
                print(sys.exc_info())
            else :
                log('Utilisateur '+username+' ajouté')
                flash('Le nouvel utilisateur '+username+' a correctement été ajouté')

    # On renvoie l'HTML avec les infos
    return render_template('adduser.html', error=error)




##########################
## Flask views : probes ##
##########################

@app.route('/manageprobes/')
def manage_probes():
    """La page web qui permet de gérer les capteurs"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # On récupère les infos sur l'ensemble des capteur
    db = get_db()
    cur = db.execute('SELECT id, name FROM probes ORDER BY id')
    probes = cur.fetchall()

    # On renvoie l'HTML avec les infos
    return render_template('manageprobes.html', probes=probes)




@app.route('/removeprobe/<int:id>/')
def remove_probe(id):
    """La page web qui permet de retirer un capteur particulier"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # On récupère les infos concernant le capteur en particulier
    db = get_db()
    cur = db.execute('SELECT name, filename FROM probes WHERE id=?', [id])
    probe = cur.fetchone()

    # On vérifie que le capteur en question existe
    if not probe :
        flash('Le capteur n\'a pas été trouvé')
    else :
        # On essaye de supprimer le capteur de la BDD
        # On oublie pas de retirer les alertes associés à ce capteur
        try :
            db.execute('DELETE FROM probes WHERE id=?', [id])
            db.commit()
            db.execute('DELETE FROM alerts WHERE probe_id=?', [id])
            db.commit()
        except :
            flash('Une erreur est survenue lors de la suppression de '+probe['name']+' de la BDD')
            print(sys.exc_info())
        else :
            # On supprime le fichier RRD qui est associé (attention irréversible)
            try :
                del_rrd(probe['filename'])
            except :
                flash('Une erreur est survenue lors de la suppression de '+probe['filename']+'.rrd')
                print(sys.exc_info())
            else:
                log('Capteur '+probe['name']+' supprimé')
                flash('Le capteur '+probe['name']+' a bien été supprimé')

    # On redirige vers la page de gestion des cpateurs
    return redirect(url_for('manage_probes'))




@app.route('/editprobe/<int:id>/', methods=['GET', 'POST'])
def edit_probe(id):
    """La page web qui permet de modifier les paramètres d'un capteur en particulier"""

    if not session.get('logged_in') :
        return redirect(url_for('login'))

    # Les erreurs qu'on remonte à l'utilisateur (si il y en a)
    error_name = None
    error_mac = None
    error_pred = None

    # On récupère les infos sur le capteur
    db = get_db()
    cur = db.execute('SELECT id, name, filename, mac, alpha, beta FROM probes WHERE id=?', [id])
    probe = cur.fetchone()

    # On vérifie que l'id demandé correspond bien à un capteur
    if not probe:
        flash('Le capteur que vous avez demandé n\'existe pas')
        return redirect(url_for('manage_probes'))

    # Si l'utilisateur demande à changer des paramètres
    if request.method == 'POST':
        # Demande de changer le nom du capteur
        if request.form['name'] and request.form['name'] != probe['name']:
            name = request.form['name']
            # On essaye de changer effectivement le nom du capteur dans la BDD
            try :
                db.execute('UPDATE probes SET name=? WHERE id=?', [name, id])
                db.commit()
            except :
                error_name = 'Une erreur est survenue lors de la modification du nom du capteur dans la base de donnée'
                print(sys.exc_info())
            else:
                log('Nom du capteur '+probe['name']+' changé en '+name)
                flash ('Le nom du capteur '+probe['name']+' a bien été changé en '+name)

        # Demande de changer la mac du capteur
        if request.form['mac'] and request.form['mac'] != probe['mac'] :
            # On vérifie que ça correspond bien à une MAC
            if not re.match('([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', request.form['mac']) :
                error_mac = 'Veuillez entrer une addresse MAC au format correct'
            else:
                mac = request.form['mac']
                # On essaye de changer la mac dans la BDD
                try :
                    db.execute('UPDATE probes SET mac=? WHERE id=?', [mac, id])
                    db.commit()
                except :
                    error_mac = 'Une erreur est survenue lors de la modification de la MAC dans la base de donnée'
                    print(sys.exc_info())
                else :
                    log('Mac du capteur '+probe['name']+' changé')
                    flash('La mac du capteur '+probe['name']+' a correctement été modifié')

        # Demande de changer un paramètre de prédiction (on ne s'embête pas à différencier les 2 cas)
        if request.form['alpha'] or request.form['beta'] :
            alpha = probe['alpha']
            beta = probe['beta']
            # On essaye de récupérer les paramètres (il faut que se soit des nombres)
            try:
                if request.form['alpha'] :
                    alpha = float(request.form['alpha'])
                if request.form['beta'] :
                    beta = float(request.form['beta'])
            except :
                error_pred = 'Veuillez entrer des nombres pour les paramètres de prédiction'
                print(sys.exc_info())
            else :
                # On essaye de changer ces paramètres dans la RRD
                try :
                    tune_rrd_pred(probe['filename'], alpha=alpha, beta=beta)
                except :
                    error_pred = 'Une erreur est survenue lors de la modification des paramètres de la RRD'
                    print(sys.exc_info())
                else :
                    # On essaye de changer les paramètres dans la BDD
                    # RQ : On est obligé de gerder une trace de ces paramètres pcq
                    #      on peut pas les récup avec rrdtool.info()
                    try :
                        db.execute('UPDATE probes SET alpha=?, beta=? WHERE id=?', [alpha, beta, id])
                        db.commit()
                    except :
                        error_pred = 'Une erreur est survenue lors de la modification des paramètres de prédiction dans la base de données. Réinitialisation des paramètres'
                        # Si échec de modif de la BDD, on oublie pas de revenir en arrière sur les modifs de RRD
                        tune_rrd_pred(probe['filename'], alpha=probe['alpha'], beta=probe['beta'])
                        print(sys.exc_info())
                    else :
                        log('Paramètres de prédiction de '+probe['name']+' changés')
                        flash('Les paramètres de prédiction de '+probe['name']+' ont correctement été changé')

    # On recharge les modifications depuis la BDD pour prendre en compte les modif effectuées
    # Nécessaire pour un affichage joli et sans ambiguité
    probe = db.execute('SELECT id, name, filename, mac, alpha, beta FROM probes WHERE id=?', [id]).fetchone()

    # On retourne l'HTML avec les infos
    return render_template('editprobe.html', probe=probe, error_name=error_name, error_mac=error_mac, error_pred=error_pred)




@app.route('/addprobe/', methods=['GET', 'POST'])
def add_probe():
    """La page web qui permet d'ajouter un capteur"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Les erreurs qu'on remonte à l'utilisateur (si il y en a)
    error = None

    # Les valeurs par défaut des paramètres
    alpha = 0.000192522
    beta = 0.00000802250
    period = 86400

    # Si l'utilisateur demande l'ajout d'un capteur
    if request.method == 'POST' :
        # On vérifie que les champs obligatoires sont remplis
        if not request.form['name'] or not request.form['mac'] :
            error = 'Les champs ne sont pas tous remplis'
        else :
            # On essaye de récupérer les paramètres de prédictions si ils existent (nombres)
            try :
                if request.form['alpha'] : alpha = float(request.form['alpha'])
                if request.form['beta'] : beta = float(request.form['beta'])
                if request.form['period'] : period = float(request.form['period'])
            except :
                error = 'Veuillez entrer des nombres pour les paramètres de prédiction'
                print(sys.exc_info())
            else :
                # On récupère le nom et on génère un nom de fichier avec qui n'existe pas déjà
                name = request.form['name']
                filename = safename(name)
                final_filename = filename
                i = 0
                while os.path.isfile(os.path.join(app.root_path, 'rrd/', final_filename+'.rrd')) :
                    i+=1
                    final_filename = filename + str(i).zfill(2)

                # On vérifie que la mac est bien une mac
                if not re.match('([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', request.form['mac']) :
                    error = 'Veuillez entrer une adrrese MAC au format correct'
                else :
                    mac = request.form['mac']

                    # On essaye de créer la RRD
                    try :
                        create_rrd(final_filename, alpha=alpha, beta=beta, period=period)
                    except :
                        error = 'Une erreur est survenue lors de la création de la RRD'
                        print(sys.exc_info())
                    else :

                        # On essaye d'ajouter ce nouveau capteur dans la BDD
                        try :
                            db = get_db()
                            db.execute('INSERT INTO probes (name, filename, mac, alpha, beta) VALUES (?, ?, ?, ?, ?)',
                                    [name, final_filename, mac, alpha, beta])
                            db.commit()
                        except :
                            error = 'Une erreur est survenue lors de l\'ajout de la sonde à la base de donnée. Suppression de '+final_filename+'.rrd'
                            # Si il y a une erreur on supprime la RRD qu'on vient de créer
                            del_rrd(final_filename)
                            print(sys.exc_info())
                        else :
                            log('Capteur '+name+' ajouté')
                            flash('La nouvelle sonde '+name+' a été correctement ajoutée')

    # On renvoie l'HTML avec les infos
    return render_template('addprobe.html', error=error)





##########################
## Flask views : alerts ##
##########################

@app.route('/managealerts/')
def manage_alerts():
    """La page web qui permet de gérer les alertes"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # On récupère les infos concernant l'ensemble des alertes
    db = get_db()
    cur = db.execute('SELECT alerts.id, alerts.email, probes.name FROM alerts JOIN probes ON alerts.probe_id=probes.id ORDER BY alerts.id')
    alerts = cur.fetchall()

    # On renvoie l'HTML avec les infos
    return render_template('managealerts.html', alerts=alerts)




@app.route('/removealert/<int:id>')
def remove_alert(id):
    """La page web qui permet de retirer une alerte en particulier"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # On récupère les infos concernant cette alerte
    db = get_db()
    cur = db.execute('SELECT id FROM alerts WHERE id=?', [id])
    alert = cur.fetchone()

    # On vérifie que l'id demandé correspond à une alerte
    if not alert :
        flash('L\'alerte demandée n\'a pas été trouvé')
    else :
        # On essaye de supprimer l'alerte correspondante
        try :
            db.execute('DELETE FROM alerts WHERE id=?', [id])
            db.commit()
        except :
            flash('Une erreur est survenue lors de la suppression de l\'alerte')
            print(sys.exc_info())
        else :
            log('Alerte n°'+str(id)+' supprimé')
            flash('L\'alerte a bien été supprimé')

    # On redirige vers la page de gestion des alertes
    return redirect(url_for('manage_alerts'))




@app.route('/editalert/<int:id>/', methods=['GET', 'POST'])
def edit_alert(id):
    """La page web permettant de modifier les paramètres d'une alerte en particulier"""

    if not session.get('logged_in') :
        return redirect(url_for('login'))

    # Les erreurs qu'on remonte à l'utilisateur (si il y en a)
    error_email = None
    error_probe = None

    # On récupère les infos concernant les capteurs (pour proposer à qui associer l'alerte)
    # et les infos concernant l'alerte en particulier
    db = get_db()
    cur = db.execute('SELECT email, probe_id FROM alerts WHERE id=?', [id])
    alert = cur.fetchone()
    cur = db.execute('SELECT id, name FROM probes')
    probes = cur.fetchall()

    # On vérifie que l'id demandé correpond bien à une alerte
    if not alert:
        flash('L\'alerte que vous avez demandé n\'existe pas')
        return redirect(url_for('manage_alerts'))

    # Si l'utilisateur demande un changement de paramètre
    if request.method == 'POST' :
        # Demande de changement de l'email
        if request.form['email'] and request.form['email'] != alert['email'] :
            # On vérifie que c'est bien un email valide (syntax check, DNS & MX record check)
            try :
                v = validate_email(request.form['email'])
                email = v['email']
            except EmailNotValidError as e :
                error_email = str(e)
                print(sys.exc_info())
            else :
                # On essaye de changer l'email dans la BDD
                try :
                    db.execute('UPDATE alerts SET email=? WHERE id=?', [email, id])
                    db.commit()
                except :
                    error_email = 'Une erreur est survenue lors de la modification de l\'email dans la base de donnée'
                    print(sys.exc_info())
                else:
                    log('Mail de l\'alerte n°'+str(id)+' changé')
                    flash ('L\'email '+alert['email']+' a bien été changé en '+email)

        # Demande de changement de capteur associé
        if request.form['probe'] and request.form['probe'] != str(alert['probe_id']) :
            # On essaye de récupérer l'id du capteur (doit être un nombre
            try :
                probe_id = int(request.form['probe'])
            except :
                error_probe = 'Veuillez ne pas foutre la merde dans les données POST ^^'
                print(sys.exc_info())
            else :
                # On vérifie que cet id correpond bien à un capteur
                if probe_id in [p['id'] for p in probes] :
                    # On change le capteur associé dans la BDD
                    try :
                        db.execute('UPDATE alerts SET probe_id=? WHERE id=?', [probe_id, id])
                        db.commit()
                    except :
                        error_probe = 'Une erreur est survenue lors de la modification du capteur associé dans la base de donnée'
                        print(sys.exc_info())
                    else :
                        log('Capteur associé à l\'alerte n°'+str(id)+' changé')
                        flash('Le capteur associé a correctement été modifié')
                else :
                    error_probe = 'Impossible de trouver le capteur que vous avez demandé'

    # On recharge les modifications depuis la BDD pour prendre en compte les modif effectuées
    # Nécessaire pour un affichage joli et sans ambiguité
    alert = db.execute('SELECT id, email, probe_id FROM alerts WHERE id=?', [id]).fetchone()

    # On renvoie l'HTML avec les infos
    return render_template('editalert.html', alert=alert, probes=probes, error_email=error_email, error_probe=error_probe)




@app.route('/addalert/', methods=['GET', 'POST'])
def add_alert():
    """La page web qui permet d'ajouter une alerte"""

    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # On récupère les infos sur les capteur (pour la sélection du capteur associé)
    db = get_db()
    cur = db.execute('SELECT id, name FROM probes')
    probes = cur.fetchall()

    # L'erreur qu'on remonte à l'utilisateur (si il y en a)
    error = None

    # Si l'utilisateur demande l'ajout d'une alerte
    if request.method == 'POST' :
        # On vérifie que les champs sont remplis
        if not request.form['email'] or not request.form['probe'] :
            error = 'Les champs ne sont pas tous remplis'
        else :
            # On essaye de récupérer l'id du capteur demandé (nombre)
            try :
                probe_id = int(request.form['probe'])
            except :
                error = 'Veuillez ne pas foutre la merde dans les données POST ^^'
                print(sys.exc_info())
            else :
                # On vérifie que l'id demandé correspond bien à un capteur
                if probe_id in [p['id'] for p in probes] :
                    # On vérifie que l'email est valide (syntax + DNS + MX check)
                    try :
                        v = validate_email(request.form['email'])
                        email = v['email']
                    except EmailNotValidError as e :
                        error = str(e)
                        print(sys.exc_info())
                    else :
                        probe_id = request.form['probe']
                        # On essaye d'ajouter l'alerte dans la BDD
                        try :
                            db.execute('INSERT INTO alerts (email, probe_id) VALUES (?, ?)',
                                    [email, probe_id])
                            db.commit()
                        except :
                            error = 'Une erreur est survenue lors de l\'ajout de l\'alerte à la base de donnée.'
                            print(sys.exc_info())
                        else :
                            log('Nouvelle alerte ajoutée')
                            flash('La nouvelle alerte a été correctement ajoutée')
                else :
                    error = 'Impossible de trouver le capteur demandé'

    # On renvoie l'HTML avec les infos
    return render_template('addalert.html', error=error, probes=probes)




#########################
## Flask views : login ##
#########################

@app.route('/login/', methods=['GET', 'POST'])
def login():
    """La page web qui permet de se connecter
        Pas besoin de vérifier qu'il est déjà connecté"""

    # L'erreur qu'on remonte à l'utilisateur (si il y en a)
    error = None

    # Si l'utilisateur envoie ses identifiants de connexion
    if request.method == 'POST':
        # On vérifie que les champs sont remplis
        if request.form['username'] and request.form['password'] :
            # On récupère les infos sur l'utilisateur demandé
            db = get_db()
            cur = db.execute('SELECT username, password, salt FROM users WHERE username=?',
                    [request.form['username']])
            user = cur.fetchone()

            # On vérifie que l'utilisateur existe
            if not user :
                error = 'Identifiants incorrects'
            else :
                # On vérifie que le mot de pass correpond
                if saltpassword(request.form['password'], user['salt']) == user['password'] :
                    session['logged_in'] = True
                    log('Utilisateur '+request.form['username']+' connecté')
                    flash('Connecté')
                    # Si connexion réussie on revient à l'acceuil (pas besoin de revenir à /login/)
                    return redirect(url_for('accueil'))
                else :
                    error = 'Identifiants incorrects'
        else :
            error = 'Aucun identifiants fourni'

    # Si connexion échouée ou méthode GET on affiche l'HTML avec les infos
    return render_template('login.html', error=error)




@app.route('/logout/')
def logout():
    """La page web qui permet de se déconnecter"""

    # On fini la session
    session.pop('logged_in', None)
    flash('Déconnecté')

    # On redirige vers l'acceuil (c'est la seule page accessible avec /login/)
    return redirect(url_for('accueil'))

