# -*- coding: utf-8 -*-

# all the imports
import os
import sys
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from hashlib import sha256
from .scripts.graph import *
from .scripts.rrd import *
from random import randint
from email_validator import validate_email, EmailNotValidError
import re

app = Flask(__name__) # create the application instance :)
app.config.from_object(__name__) # load config from this file , kerrucent.py

# Load default config and override config from an environment variable
app.config.update(dict(
    DBSCHEMA=os.path.join(app.root_path, 'db/', 'schema.sql'),
    DATABASE=os.path.join(app.root_path, 'db/', 'kerrucent.db'),
    SECRET_KEY='development key',
))
app.config.from_envvar('KERRUCENT_SETTINGS', silent=True)

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
    print('Initialized the database.')

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


def saltpassword (password, salt) :
    """Return a salted password according to the algorithm chosen"""
    saltedpassword = password + str(salt)
    return sha256(saltedpassword.encode('utf-8')).hexdigest()







@app.route('/')
def accueil() :
    return render_template('accueil.html')



@app.route('/apercu/')
def apercu() :
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('SELECT id, name, filename FROM probes ORDER BY id')
    probes = cur.fetchall()
    images = {}
    for p in probes :
        images[p['id']] = graph_accueil(p['filename'], p['name'], width=550, height=300)['image_info']
    return render_template('apercu.html', probes=probes, images=images)



@app.route('/detail/<int:id>/', methods=['GET', 'POST'])
def detail(id) :
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('SELECT id, name, filename, mac FROM probes WHERE id=?', [id])
    probe = cur.fetchone()

    if not probe :
        abort(404)

    time = Duree.j1
    grandeurs = []

    if request.method == 'POST' :

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

    if len(grandeurs) == 0 :
        grandeurs.append(Grandeur.courant)

    image = graph_detail(probe['filename'], probe['name'], time, grandeurs, width=1000, height=500)['image_info']

    return render_template('detail.html', probe=probe, image=image)



@app.route('/manageusers/')
def manage_users():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('SELECT id, username FROM users ORDER BY id')
    users = cur.fetchall()

    return render_template('manageusers.html', users=users)



@app.route('/removeuser/<int:id>/')
def remove_user(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('SELECT username FROM users WHERE id=?', [id])
    user = cur.fetchone()

    if not user :
        flash('L\'utilisateur n\'a pas été trouvé')
    else :
        try :
            db.execute('DELETE FROM users WHERE id=?', [id])
            db.commit()
        except :
            flash ('Une erreur est survenue lors de la suppression de '+user['username']+' de la BDD')
        else :
            flash('L\'utilisateur '+user['username']+' a bien été supprimé')

    return redirect(url_for('manage_users'))



@app.route('/edituser/<int:id>/', methods=['GET', 'POST'])
def edit_user(id):
    if not session.get('logged_in') :
        return redirect(url_for('login'))

    error_name = None
    error_pass = None

    db = get_db()
    cur = db.execute('SELECT id, username FROM users WHERE id=?', [id])
    user = cur.fetchone()

    if not user:
        flash('L\'utilisateur que vous avez demandé n\'existe pas')
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        if request.form['username'] and request.form['username'] != user['username']:      # On change le nom d'utilisateur
            username = request.form['username']
            try :
                db.execute('UPDATE users SET username=? WHERE id=?',
                        [username, id])
                db.commit()
            except :
                error_name = 'Une erreur est survenue lors de la modification du nom d\'utilisateur dans la base de donnée'
                print(sys.exc_info())
            else:
                flash ('Le nom d\'utilisateur de '+user['username']+' a bien été changé en '+username)


        if request.form['password1'] or request.form['password2'] :    # On change le mot de passe
            if not request.form['password1'] or not request.form['password2'] :
                error_pass = 'Veuillez compléter les deux champs'
            elif request.form['password1'] != request.form['password2'] :
                error_pass = 'Les deux mot de passe ne correspondent pas'
            else :
                password = request.form['password1']
                salt = randint(1000000, 1000000000)
                try :
                    db.execute('UPDATE users SET password=?, salt=? WHERE id=?',
                            [saltpassword(password, salt), salt, id])
                    db.commit()
                except :
                    error_pass = 'Une erreur est survenue lors de la modification du mot de passe dans la base de donnée'
                    print(sys.exc_info())
                else :
                    flash('Le mot de passe de '+user['username']+' a correctement été modifié')

    return render_template('edituser.html', user=user, error_name=error_name, error_pass=error_pass)



@app.route('/adduser/', methods=['GET', 'POST'])
def add_user():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    error = None
    if request.method == 'POST' :
        if not request.form['username'] or not request.form['password1'] or not request.form['password2'] :
            error = 'Les champs ne sont pas tous remplis'
        elif request.form['password1'] != request.form['password2'] :
            error = 'Les deux mot de passe ne correspondent pas'
        else :
            username = request.form['username']
            password = request.form['password1']
            salt = randint(1000000, 1000000000)

            try :
                db = get_db()
                db.execute('INSERT INTO users (username, password, salt) VALUES (?, ?, ?)',
                            [username, saltpassword(password, salt), salt])
                db.commit()
            except :
                error = 'Une erreur est survenue lors de l\'ajout de l\'utilisateur à la base de données'
                print(sys.exc_info())
            else :
                flash('Le nouvel utilisateur '+username+' a correctement été ajouté')

    return render_template('adduser.html', error=error)



@app.route('/manageprobes/')
def manage_probes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('SELECT id, name FROM probes ORDER BY id')
    probes = cur.fetchall()

    return render_template('manageprobes.html', probes=probes)



@app.route('/removeprobe/<int:id>/')
def remove_probe(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('SELECT name, filename FROM probes WHERE id=?', [id])
    probe = cur.fetchone()

    if not probe :
        flash('Le capteur n\'a pas été trouvé')
    else :
        try :
            db.execute('DELETE FROM probes WHERE id=?', [id])
            db.commit()
            db.execute('DELETE FROM alerts WHERE probe_id=?', [id])
            db.commit()
        except :
            flash('Une erreur est survenue lors de la suppression de '+probe['name']+' de la BDD')
            print(sys.exc_info())
        else :
            try :
                del_rrd(probe['filename'])
            except :
                flash('Une erreur est survenue lors de la suppression de '+probe['filename']+'.rrd')
                print(sys.exc_info())
            else:
                flash('Le capteur '+probe['name']+' a bien été supprimé')


    return redirect(url_for('manage_probes'))



@app.route('/editprobe/<int:id>/', methods=['GET', 'POST'])
def edit_probe(id):
    if not session.get('logged_in') :
        return redirect(url_for('login'))

    error_name = None
    error_mac = None
    error_pred = None

    db = get_db()
    cur = db.execute('SELECT id, name, filename, mac, alpha, beta FROM probes WHERE id=?', [id])
    probe = cur.fetchone()

    if not probe:
        flash('Le capteur que vous avez demandé n\'existe pas')
        return redirect(url_for('manage_probes'))

    if request.method == 'POST':
        if request.form['name'] and request.form['name'] != probe['name']:      # On change le nom du capteur
            name = request.form['name']
            try :
                db.execute('UPDATE probes SET name=? WHERE id=?', [name, id])
                db.commit()
            except :
                error_name = 'Une erreur est survenue lors de la modification du nom du capteur dans la base de donnée'
                print(sys.exc_info())
            else:
                flash ('Le nom du capteur '+probe['name']+' a bien été changé en '+name)


        if request.form['mac'] and request.form['mac'] != probe['mac'] :    # On change la MAC
            if not re.match('([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', request.form['mac']) :
                error_mac = 'Veuillez entrer une addresse MAC au format correct'
            else:
                mac = request.form['mac']
                try :
                    db.execute('UPDATE probes SET mac=? WHERE id=?', [mac, id])
                    db.commit()
                except :
                    error_mac = 'Une erreur est survenue lors de la modification de la MAC dans la base de donnée'
                    print(sys.exc_info())
                else :
                    flash('La mac du capteur '+probe['name']+' a correctement été modifié')

        if request.form['alpha'] or request.form['beta'] :      # On change les paramètres de prédiction
            alpha = probe['alpha']
            beta = probe['beta']
            try:
                if request.form['alpha'] :
                    alpha = float(request.form['alpha'])
                if request.form['beta'] :
                    beta = float(request.form['beta'])
            except :
                error_pred = 'Veuillez entrer des nombres pour les paramètres de prédiction'
                print(sys.exc_info())
            else :
                try :
                    tune_rrd_pred(probe['filename'], alpha=alpha, beta=beta)
                except :
                    error_pred = 'Une erreur est survenue lors de la modification des paramètres de la RRD'
                    print(sys.exc_info())
                else :
                    try :
                        db.execute('UPDATE probes SET alpha=?, beta=? WHERE id=?', [alpha, beta, id])
                        db.commit()
                    except :
                        error_pred = 'Une erreur est survenue lors de la modification des paramètres de prédiction dans la base de données. Réinitialisation des paramètres'
                        tune_rrd_pred(probe['filename'], alpha=probe['alpha'], beta=probe['beta'])
                        print(sys.exc_info())
                    else :
                        flash('Les paramètres de prédiction de '+probe['name']+' ont correctement été changé')


    return render_template('editprobe.html', probe=probe, error_name=error_name, error_mac=error_mac, error_pred=error_pred)



@app.route('/addprobe/', methods=['GET', 'POST'])
def add_probe():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    error = None
    alpha = 0.000192522
    beta = 0.00000802250
    period = 86400
    if request.method == 'POST' :
        if not request.form['name'] or not request.form['mac'] :
            error = 'Les champs ne sont pas tous remplis'
        else :
            try :
                if request.form['alpha'] : alpha = float(request.form['alpha'])
                if request.form['beta'] : beta = float(request.form['beta'])
                if request.form['period'] : period = float(request.form['period'])
            except :
                error = 'Veuillez entrer des nombres pour les paramètres de prédiction'
                print(sys.exc_info())
            else :
                name = request.form['name']
                filename = safename(name)
                final_filename = filename
                i = 0
                while os.path.isfile(os.path.join(app.root_path, 'rrd/', final_filename+'.rrd')) :
                    i+=1
                    final_filename = filename + str(i).zfill(2)
                if not re.match('([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', request.form['mac']) :
                    error = 'Veuillez entrer une adrrese MAC au format correct'
                else :
                    mac = request.form['mac']
                    try :
                        create_rrd(final_filename, alpha=alpha, beta=beta, period=period)
                    except :
                        error = 'Une erreur est survenue lors de la création de la RRD'
                        print(sys.exc_info())
                    else :
                        try :
                            db = get_db()
                            db.execute('INSERT INTO probes (name, filename, mac, alpha, beta) VALUES (?, ?, ?, ?, ?)',
                                    [name, final_filename, mac, alpha, beta])
                            db.commit()
                        except :
                            error = 'Une erreur est survenue lors de l\'ajout de la sonde à la base de donnée. Suppression de '+final_filename+'.rrd'
                            del_rrd(final_filename)
                            print(sys.exc_info())
                        else :
                            flash('La nouvelle sonde '+name+' a été correctement ajoutée')

    return render_template('addprobe.html', error=error)


@app.route('/managealerts/')
def manage_alerts():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('SELECT alerts.id, alerts.email, probes.name FROM alerts JOIN probes ON alerts.probe_id=probes.id ORDER BY alerts.id')
    alerts = cur.fetchall()

    return render_template('managealerts.html', alerts=alerts)




@app.route('/removealert/<int:id>')
def remove_alert(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('SELECT id FROM alerts WHERE id=?', [id])
    alert = cur.fetchone()

    if not alert :
        flash('L\'alerte demandée n\'a pas été trouvé')
    else :
        try :
            db.execute('DELETE FROM alerts WHERE id=?', [id])
            db.commit()
        except :
            flash('Une erreur est survenue lors de la suppression de l\'alerte')
            print(sys.exc_info())
        else :
            flash('L\'alerte a bien été supprimé')


    return redirect(url_for('manage_alerts'))




@app.route('/editalert/<int:id>/', methods=['GET', 'POST'])
def edit_alert(id):
    if not session.get('logged_in') :
        return redirect(url_for('login'))

    error_email = None
    error_probe = None

    db = get_db()
    cur = db.execute('SELECT email, probe_id FROM alerts WHERE id=?', [id])
    alert = cur.fetchone()
    cur = db.execute('SELECT id FROM probes')
    probes = cur.fetchall()

    if not alert:
        flash('L\'alerte que vous avez demandé n\'existe pas')
        return redirect(url_for('manage_alerts'))

    if request.method == 'POST':
        if request.form['email'] and request.form['email'] != alert['email']:      # On change l'email
            try :
                v = validate_email(request.form['email'])
                email = v['email']
            except EmailNotValidError as e :
                error_email = str(e)
                print(sys.exc_info())
            else :
                try :
                    db.execute('UPDATE alerts SET email=? WHERE id=?', [email, id])
                    db.commit()
                except :
                    error_email = 'Une erreur est survenue lors de la modification de l\'email dans la base de donnée'
                    print(sys.exc_info())
                else:
                    flash ('L\'email '+alert['email']+' a bien été changé en '+email)


        if request.form['probe'] and request.form['probe'] != str(alert['probe_id']) :    # On change le capteur associé
            try :
                probe_id = int(request.form['probe'])
            except :
                error_probe = 'Veuillez ne pas foutre la merde dans les données POST ^^'
                print(sys.exc_info())
            else :
                if probe_id in [p['id'] for p in probes] :
                    try :
                        db.execute('UPDATE alerts SET probe_id=? WHERE id=?', [probe_id, id])
                        db.commit()
                    except :
                        error_probe = 'Une erreur est survenue lors de la modification du capteur associé dans la base de donnée'
                        print(sys.exc_info())
                    else :
                        flash('Le capteur associé a correctement été modifié')
                else :
                    error_probe = 'Impossible de trouver le capteur que vous avez demandé'

    alert = db.execute('SELECT id, email, probe_id FROM alerts WHERE id=?', [id]).fetchone()
    probes = db.execute('SELECT id, name FROM probes').fetchall()

    return render_template('editalert.html', alert=alert, probes=probes, error_email=error_email, error_probe=error_probe)



@app.route('/addalert/', methods=['GET', 'POST'])
def add_alert():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('SELECT id, name FROM probes')
    probes = cur.fetchall()

    error = None
    if request.method == 'POST' :
        if not request.form['email'] or not request.form['probe'] :
            error = 'Les champs ne sont pas tous remplis'
        else :
            try :
                probe_id = int(request.form['probe'])
            except :
                error = 'Veuillez ne pas foutre la merde dans les données POST ^^'
                print(sys.exc_info())
            else :
                if probe_id in [p['id'] for p in probes] :
                    try :
                        v = validate_email(request.form['email'])
                        email = v['email']
                    except EmailNotValidError as e :
                        error = str(e)
                        print(sys.exc_info())
                    else :
                        probe_id = request.form['probe']
                        try :
                            db.execute('INSERT INTO alerts (email, probe_id) VALUES (?, ?)',
                                    [email, probe_id])
                            db.commit()
                        except :
                            error = 'Une erreur est survenue lors de l\'ajout de l\'alerte à la base de donnée.'
                            print(sys.exc_info())
                        else :
                            flash('La nouvelle alerte a été correctement ajoutée')
                else :
                    error = 'Impossible de trouver le capteur demandé'
    return render_template('addalert.html', error=error, probes=probes)




@app.route('/login/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] and request.form['password'] :
            db = get_db()
            cur = db.execute('SELECT username, password, salt FROM users WHERE username=?',
                    [request.form['username']])
            user = cur.fetchone()
            if not user :
                error = 'Identifiants incorrects'
            else :
                if saltpassword(request.form['password'], user['salt']) == user['password'] :
                    session['logged_in'] = True
                    flash('Connecté')
                    return redirect(url_for('accueil'))
                else :
                    error = 'Identifiants incorrects'
        else :
            error = 'Aucun identifiants fourni'
    return render_template('login.html', error=error)



@app.route('/logout/')
def logout():
    session.pop('logged_in', None)
    flash('Déconnecté')
    return redirect(url_for('accueil'))

