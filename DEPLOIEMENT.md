# Déploiement en production (Nginx + Gunicorn)

Ce guide décrit la mise en service sur un serveur Linux de l'université. Les
noms de domaine, chemins et comptes ci-dessous sont des exemples à remplacer.
**Ne commitez jamais** de vraies valeurs (mots de passe, clés) dans ce dépôt.

## 1. Préparation

1. Créer un compte MySQL **dédié** à l'application, avec les droits sur la seule base `edt_uccb` (jamais `root`) :
   ```sql
   CREATE USER 'edt_app'@'localhost' IDENTIFIED BY '<mot de passe long et aléatoire>';
   GRANT ALL PRIVILEGES ON edt_uccb.* TO 'edt_app'@'localhost';
   ```
2. Créer le fichier `.env` sur le serveur (modèle : `.env.example`), lisible par le seul compte qui lance l'application (`chmod 600 .env`). Générer une **nouvelle** `DJANGO_SECRET_KEY` propre à ce serveur.
3. Installer : `pip install -r requirements.txt`, puis `python manage.py migrate`, `python manage.py collectstatic`.
4. Construire le frontend : `cd edt-frontend && npm ci && npm run build` (dossier `dist/`, servi par Nginx ; ne jamais exposer le serveur de développement Vite).

Sans `DJANGO_SECRET_KEY`, Django refuse de démarrer en production : c'est voulu.

## 2. Gunicorn

Écouter uniquement sur une socket ou sur `127.0.0.1`, **jamais** sur une interface publique :

```
gunicorn Gestion_edt.wsgi:application --bind unix:/run/edt/gunicorn.sock --workers 3
```

Le cache fichier de production (`DJANGO_CACHE_DIR`, par défaut `./cache`) doit être accessible en écriture par tous les workers : il porte les compteurs de limitation de débit.

## 3. Nginx (exemple)

```nginx
# Limitation de débit supplémentaire sur la connexion (en plus de celle de Django)
limit_req_zone $binary_remote_addr zone=edt_login:10m rate=30r/m;
# 429 (« trop de requêtes ») au lieu de 503 : l'interface affiche alors « Trop
# de tentatives » et non « Le serveur a rencontré une erreur » (Phase B).
limit_req_status 429;

# HSTS : Django le pose sur les réponses de l'API, nginx sur tout le reste
# (pages de l'interface). Jamais les deux : deux en-têtes HSTS sont contraires
# à la norme (relevé par le scan ZAP de la Phase B). Un en-tête vide n'est
# pas envoyé.
map $upstream_http_strict_transport_security $hsts_nginx {
    ""      "max-age=3600";
    default "";
}

server {
    # nginx 1.25.1 et plus : avertissement « listen ... http2 is deprecated »,
    # sans conséquence ; on peut alors écrire `listen 443 ssl;` + `http2 on;`.
    listen 443 ssl http2;
    server_name edt.exemple-universite.org;
    # ssl_certificate / ssl_certificate_key : certificat de l'université

    client_max_body_size 20m;            # aligné sur DOCUMENT_MAX_UPLOAD_BYTES
    server_tokens off;                   # ne pas annoncer la version de nginx (scan ZAP)

    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy same-origin always;
    add_header X-Frame-Options DENY always;
    # HSTS des pages de l'interface (voir le `map` plus haut). Même durée que
    # DJANGO_HSTS_SECONDS : les monter ensemble (§4).
    add_header Strict-Transport-Security $hsts_nginx always;
    # Politique de contenu stricte : aucun script hors des fichiers de
    # l'application (ni script en ligne, ni domaine extérieur). C'est la
    # parade principale si une faille permettait d'injecter du code, car les
    # jetons de session sont rangés dans le navigateur (localStorage).
    # Vérifiée le 2026-10-01 sur l'interface construite (planning chef et
    # étudiant, changement de semaine, export PDF) : aucun blocage. Les
    # domaines Google ne servent qu'aux polices (src/index.css, index.html) ;
    # à retirer si les polices sont un jour hébergées avec l'application.
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' data: https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;

    # Frontend (fichiers construits)
    root /srv/edt/edt-frontend/dist;
    location / { try_files $uri /index.html; }

    location /static/ { alias /srv/edt/staticfiles/; }

    # API
    location /api/ {
        proxy_pass http://unix:/run/edt/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        # ÉCRASER (et non ajouter à) l'en-tête envoyé par le client : Django
        # s'en sert pour identifier l'adresse réelle (DJANGO_NUM_PROXIES=1).
        proxy_set_header X-Forwarded-For $remote_addr;
    }
    location = /api/token/ {
        limit_req zone=edt_login burst=10 nodelay;
        proxy_pass http://unix:/run/edt/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
    }

    # Administration Django : réseau interne uniquement
    location /admin/ {
        allow 10.0.0.0/8;                # à adapter au réseau de l'université
        deny all;
        proxy_pass http://unix:/run/edt/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $remote_addr;
    }

    # Documents pédagogiques : JAMAIS accessibles directement. Django vérifie
    # les droits (GET /api/documents/<id>/telecharger/) puis répond avec
    # X-Accel-Redirect ; Nginx envoie alors le fichier. `internal` interdit tout
    # accès direct depuis l'extérieur.
    location /protected_media/ {
        internal;
        alias /var/lib/edt/media/;
    }

    # Photos de profil : affichées par de simples <img>, donc sans jeton. Leurs
    # noms contiennent un identifiant aléatoire non devinable.
    location /media/profils/ { alias /var/lib/edt/media/profils/; }
    # Tout le reste de /media/ est refusé.
    location /media/ { return 404; }
}

server {                                  # redirection HTTP -> HTTPS
    listen 80;
    server_name edt.exemple-universite.org;
    return 301 https://$host$request_uri;
}
```

Variables `.env` correspondantes :

```
DJANGO_MEDIA_ROOT=/var/lib/edt/media
DJANGO_ALLOWED_HOSTS=edt.exemple-universite.org
DJANGO_CORS_ALLOWED_ORIGINS=https://edt.exemple-universite.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://edt.exemple-universite.org
DJANGO_PROTECTED_MEDIA_PREFIX=/protected_media/
```

`DJANGO_PROTECTED_MEDIA_PREFIX` active la livraison par `X-Accel-Redirect`. Vide (défaut, développement), Django envoie lui-même le fichier.

## 4. HSTS

Démarrer avec `DJANGO_HSTS_SECONDS=3600` (1 h). Une fois HTTPS confirmé stable, passer à `31536000` (1 an), **en même temps** dans le `.env` et dans le `map ... $hsts_nginx` de nginx. Les navigateurs mémorisent HSTS : on ne peut pas le « défaire » côté serveur. `DJANGO_HSTS_INCLUDE_SUBDOMAINS` : uniquement si **tous** les sous-domaines du domaine sont servis en HTTPS.

`manage.py check --deploy` signale deux avertissements qui relèvent de ce choix (`W005` sous-domaines, `W021` liste « preload ») : ils sont volontairement laissés à l'appréciation de l'équipe.

## 5. Entretien

- Purger périodiquement les jetons expirés de la liste noire (cron quotidien) : `python manage.py flushexpiredtokens`.
- Surveiller `logs/django.log` (ou `DJANGO_LOG_DIR`).
- Sauvegarder la base **et** le dossier `DJANGO_MEDIA_ROOT` : les documents et photos ne sont plus dans git.
  - Base : `mysqldump --single-transaction --routines --triggers --no-tablespaces edt_uccb > edt_uccb-AAAA-MM-JJ.sql` (identifiants dans un fichier d'options `--defaults-extra-file`, jamais en ligne de commande), chaque nuit, copie hors du serveur.
  - Fichiers : copie du dossier `DJANGO_MEDIA_ROOT` à la même heure (`rsync -a`).
  - Une sauvegarde ne vaut que si on sait la restaurer : voir l'essai du §7.
- Après tout changement de `DJANGO_SECRET_KEY`, tous les utilisateurs doivent se reconnecter.

## 6. Contrôle avant ouverture

```
DJANGO_DEBUG=False python manage.py check --deploy
```

Aucun avertissement de sécurité ne doit rester, à part les deux du §4 si vous les acceptez.

## 7. Vérifications le jour de la mise en ligne (Phase B)

Outils du dossier `deploiement/`, déjà rodés sur une simulation locale (§8).

1. **Contrôle du site**, depuis un ordinateur **hors** du réseau interne (Python seul suffit) :
   ```
   python deploiement/verifier_production.py --url https://edt.exemple-universite.org \
       --identifiant <compte étudiant de test> --document <numéro d'un document de ce compte>
   ```
   Le mot de passe est demandé au clavier. Contrôles : certificat et TLS, redirection HTTP → HTTPS, en-têtes de sécurité (HSTS, CSP...), version de nginx masquée, mode débogage coupé, `/admin/`, `/media/` et `/protected_media/` fermés, envoi de plus de 20 Mo refusé par nginx, téléchargement protégé (et son type), temps de connexion, rafale de connexions freinée malgré de faux `X-Forwarded-For`. Attendu : aucun ÉCHEC. Le dernier contrôle bloque les connexions depuis cet ordinateur pendant une minute (`--sans-rafale` pour le sauter).
2. **Contrôles extérieurs**, si l'adresse est publique : securityheaders.com et ssllabs.com/ssltest (note A attendue).
3. **Sauvegarde puis restauration**, sur le serveur, avec le `.env` de production :
   ```
   python deploiement/essai_sauvegarde.py --base edt_uccb
   ```
   Restaure dans `edt_uccb_restauration`, compare chaque table, puis supprime cette copie. Le compte de l'application doit pouvoir la créer : `GRANT ALL PRIVILEGES ON edt_uccb_restauration.* TO 'edt_app'@'localhost';`.
4. **Charge et scan d'attaque** : sur une instance de test du serveur (mêmes réglages, bases jetables `edt_charge` et `edt_zap`, clé secrète propre à l'instance), jamais sur la base réelle :
   - `charge/locustfile.py` (paliers 25, 50, 100 utilisateurs ; objectif : 95 % des plannings en moins de 2 s à 100 utilisateurs, aucune erreur serveur) ;
   - `zap/lancer_zap.py --cible https://<instance de test> --cle-secrete <fichier>` (rapports à trier comme au point 46 de `CORRECTIONS_A_FAIRE.md`).

## 8. Répétition locale sous Windows (simulation)

```
.venv/Scripts/python.exe deploiement/simulation_production.py [--base edt_charge|edt_zap] [--garder <minutes>]
```

Monte sur un poste Windows l'équivalent de ce guide : Django en production (`DJANGO_DEBUG=False`, HTTPS, X-Accel-Redirect) servi par waitress, derrière nginx pour Windows configuré avec le bloc nginx du §3 lui-même (lu dans ce fichier, puis adapté aux ports 8443/8081 et aux chemins de la machine), certificat auto-signé, base jetable. Puis lance `verifier_production.py`. Prérequis : nginx pour Windows (nginx.org, rangé dans `%LOCALAPPDATA%\edt-phase-b\`), `pip install waitress`, openssl (fourni avec Git), interface construite (`npm run build`).

Limites propres à Windows, sans objet sur le serveur Linux :
- le cache fichier (compteurs de limitation) produit des erreurs 500 sous requêtes simultanées (fichier verrouillé pendant son remplacement) : ne jamais faire tourner l'application en production sous Windows avec ce cache ;
- `localhost` est d'abord essayé en IPv6, où nginx n'écoute pas : viser `127.0.0.1` pour les tests de charge ;
- un seul processus waitress (pas trois workers gunicorn) et tout sur la même machine : les temps mesurés sont pessimistes.

Si le nom de domaine du vrai serveur a une adresse IPv6 (enregistrement AAAA), ajouter `listen [::]:443 ssl http2;` et `listen [::]:80;` à la configuration nginx.
