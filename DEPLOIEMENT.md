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

server {
    listen 443 ssl http2;
    server_name edt.exemple-universite.org;
    # ssl_certificate / ssl_certificate_key : certificat de l'université

    client_max_body_size 20m;            # aligné sur DOCUMENT_MAX_UPLOAD_BYTES

    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy same-origin always;
    add_header X-Frame-Options DENY always;
    # À affiner : ouvrir l'application, regarder la console du navigateur, et
    # autoriser explicitement ce qui est réellement chargé (polices, etc.).
    add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;

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

Démarrer avec `DJANGO_HSTS_SECONDS=3600` (1 h). Une fois HTTPS confirmé stable, passer à `31536000` (1 an). Les navigateurs mémorisent HSTS : on ne peut pas le « défaire » côté serveur. `DJANGO_HSTS_INCLUDE_SUBDOMAINS` : uniquement si **tous** les sous-domaines du domaine sont servis en HTTPS.

`manage.py check --deploy` signale deux avertissements qui relèvent de ce choix (`W005` sous-domaines, `W021` liste « preload ») : ils sont volontairement laissés à l'appréciation de l'équipe.

## 5. Entretien

- Purger périodiquement les jetons expirés de la liste noire (cron quotidien) : `python manage.py flushexpiredtokens`.
- Surveiller `logs/django.log` (ou `DJANGO_LOG_DIR`).
- Sauvegarder la base **et** le dossier `DJANGO_MEDIA_ROOT` : les documents et photos ne sont plus dans git.
- Après tout changement de `DJANGO_SECRET_KEY`, tous les utilisateurs doivent se reconnecter.

## 6. Contrôle avant ouverture

```
DJANGO_DEBUG=False python manage.py check --deploy
```

Aucun avertissement de sécurité ne doit rester, à part les deux du §4 si vous les acceptez.
