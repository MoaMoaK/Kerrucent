## Synopsis

Kerrucent est un système de gestion de capteurs distribués de consommation électrique réalisé dans le cadre d'un projet système de 2ème année à CentraleSupélec Campus de Rennes. Nous (les étudiants à l'origine de ce projet) sont Maël Kervella, Pierre Ruffy et Alexandre Vincent. Ce projet fût encadré par Guillaume Piolle et Jacques Weiss.

## Fonctionnalités

Le système permet via une interface web d'avoir un aperçu des capteurs en cours de surveillance. De plus le détail de chacune des grandeurs observées (courant, tension, déphasage, puissance active, puissance réactive, puissance apparente) est disponible sur plusieurs durées et permet d'appronfidire l'étude de sa consommation électique.
L'algorithme de Holt-Winter Forecasting est aussi appliqué aux données et permet de prévoir l'évolution future de la consommation et en déduire le comportement normal. Si le comportement réel semble abérant, l'utilisateur est automatiquement prévenu par le biais d'un ou de plusieurs mails qu'il aura préalablement renseigné et invité à se renseigner sur l'origine du problème.

## Technologies utilisés

Kerrucent est réalisé principalement grâce à [Flask](http://flask.pocoo.org/). Il est donc codé en Python. Pour le stockage des données comme les utilisateurs ou les alertes, on utilise un simple base de données [SQLite](https://sqlite.org/). En ce qui concerne le stockage des données de consommation électrique on utilise [RRDTool](http://oss.oetiker.ch/rrdtool/) qui est fortement spécialisé dans le stockage de données temporelles et nous permet d'accéder facilement à des graphes et à des données de prédiction qui y sont déjà implémentés.

## Installation

On commence par se placer dans le dossier d'installation

```cd /path/to/install/dir/```

```mkdir kerucent```

```cd kerrucent```

puis on clone le projet

```git clone <uri>```

On installe ensuite python (>=3.4) et pip

```apt-get install python3.4 pip```

Il peut être nécessaire de changer à la main la version de python

```ln -s /usr/bin/python /usr/bin/python3.4```

Ensuite il reste à installer [Flask](http://flask.pocoo.org/)

```pip install Flask```

Et voilà, la configuration initiale est maintenant prête, il reste plus qu'à lancer le serveur web. L'utilisation d'un screen est fortement conseillée.

## Configuration initiale

Il faut au préalable initialiser la base de données SQLite :

```flask initdb```

## Lancement du serveur

Pour l'exemple, le serveur sera lancé sur le port 80 mais attention il faut pour celà posséder les accès administrateur ce qui n'est pas nécessaire pour des ports n'appartenant pas à ceux réservés.
Il faut d'abord s'assurer qu'aucun autre service n'occupe déjà le port choisi (exemple de apache2 qui empêche flask de se lancer sur le port 80) :

```netstat -tap```

Puis on prépare l'environnement à lancer le serveur :

```export FLASK_APP=kerrucent```

Enfin, on peut lancer le serveur qui ne devrait plus poser de problème

```flask run --host=kerrucent.rez-rennes.fr --port=80```

