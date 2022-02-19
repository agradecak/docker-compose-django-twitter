---
author: Andrija Gradečak
---

# Stvaranje infrastrukture za izvođenje Twitter-like web aplikacije pomoću Docker Compose-a

## Opis aplikacije

`django-tviter` je pojednostavljena aplikacija nalik Twitter-u, u kojoj imamo Twitter korisnike (*tviteras*-e) i njihove Tweet-ove (*tvit*-ove).  
Svaki *tvit* je vezan uz jednog *tviteras*-a, a popis svih *tvit*-ova nalazimo na url-u `https://localhost/tvitovi/`.  
`https://localhost/tvitovi/` zove `ListView` pogled `TvitoviList` koji ispisuje sve *tvit*-ove zajedno sa njihovim autorima i vremenom post-anja.

## Korišteni servisi

Aplikacija `django-tviter` koristi 4 servisa:

- app - `Django` aplikacija čiji se HTTP zahtjevi obrađuju preko `gunicorn`-a
- server - `nginx` web server
- baza - `PostgreSQL` baza podataka
- cache - `Memcached` sustav za cache-ing

`gunicorn` je Python-ov web server gateway interface(WSGI) koji će procesirati HTTP zahtjeve.  
`nginx` web server će nam služiti kao proxy te za serviranje statičnih datoteka.  
`PostgreSQL` baza podataka za migriranje modela aplikacije u tablice i serviranje podataka.  
`Memcached` memory-caching sustav za cache-iranje pogleda `TvitoviList`.  

## Početno postavljanje

Prvo dohvaćamo udaljeni repozitorij koji sadrži kod naše Django aplikacije:

``` shell
$ git clone https://github.com/proto-forma/django-tviter.git
Cloning into 'django-tviter'...
remote: Enumerating objects: 45, done.
remote: Counting objects: 100% (45/45), done.
remote: Compressing objects: 100% (32/32), done.
remote: Total 45 (delta 20), reused 27 (delta 8), pack-reused 0
Receiving objects: 100% (45/45), 7.68 KiB | 7.68 MiB/s, done.
Resolving deltas: 100% (20/20), done.
```

Zatim se pozicioniramo u stvoreni direktorij:

``` shell
$ cd django-tviter
```

Unutar direktorija stvaramo datoteku `.env`:

``` shell
$ touch .env
```

`.env` datoteka sadrži sve varijable okoline kojima će se služiti servisi aplikacije.  
Prve tri dolje navedene varijable koristi `PostgreSQL` baza, dok ostale koristi naša `Django` aplikacija.

``` conf
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
POSTGRES_DB="postgres"
DB_ENGINE="django.db.backends.postgresql"
DB_NAME="postgres"
DB_USERNAME="postgres"
DB_PASSWORD="postgres"
DB_HOST="baza"
DB_PORT="5432"
DJANGO_SECRET_KEY="django-insecure-36ds%8)4_xxb-gm5t-5!x3x1uqqgeqc+3si2^gb8w1(wx4y7i="
ALLOWED_HOSTS="localhost 127.0.0.1 0.0.0.0 [::1]"
DEBUG="True"
```

Želimo stvoriti slijedeće tri datoteke:

- `requirements.txt` za navođenje Python paketa koji su nam potrebni
- `Dockerfile` za postavljanje okoline i instalaciju paketa navedenih u `requirements.txt`
- `docker-compose.yml` za orkestraciju kontejnera tj. definiranje servisa kojima ćemo se koristiti

Stvorimo navedene datoteke:

``` shell
$ touch Dockerfile docker-compose.yml requirements.txt
```

## requirements.txt

Sadržaj datoteke `requirements.txt` prikazan je ispod. `psycopg2` je paket koji nam treba za `PostgreSQL` bazu podataka. `pymemcache` je paket potreban za `Memcached` sustav cache-iranja.

``` python
Django==4.0
gunicorn==20.1.0
psycopg2>=2.8
pymemcache>=3.2
```

## Dockerfile

Sadržaj datoteke `Dockerfile` prikazan je ispod. Dohvaćamo sliku kontejnera za `Python`, radimo instalaciju `PostgreSQL`-a i paketa o kojima zavisi, nadograđujemo `pip`, instaliramo pakete navedene u `requirements.txt` i naposljetku kopiramo cijeli sadržaj trenutnog foldera u sliku.

``` dockerfile
FROM python:3.9-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
```

## docker-compose.yml

Sadržaj datoteke `docker-compose.yml` prikazan je ispod. Orkestriramo četiri kontejnera: `server`, `baza`, `cache` i `app`. `server` je `nginx` web server koji služi aplikaciju i statične datoteke(za npr. admin panel), a sluša na vratima `80` te ovisi o servisu `app`. `baza` je `PostgreSQL` baza podataka koja će služiti podatke iz baze i slušati na vratima `5432`. `cache` je `Memcached` memory-caching server koji sluša na vratima `11211`. `app` je kontejner za našu aplikaciju koji pri pokretanju vrši migracije, skuplja statične datoteke, sluša za HTTP zahtjeve na vratima `8000` pomoću `gunicorn`-a, a zavisi o servisima `baza` i `cache`. Definiramo i korištene `volumes` - jedan za `PostgreSQL` bazu, a drugi za statične datoteke aplikacije.

``` yaml
version: "3.9"
   
services:
  server:
    container_name: server
    restart: on-failure
    image: nginx:1.20-alpine
    volumes:
      - ./nginx/prod/nginx.conf:/etc/nginx/conf.d/default.conf
      - static_volume:/app/static
    ports:
      - 80:80
    depends_on:
      - app
  baza:
    container_name: baza
    image: postgres:12.0-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    env_file:
      .env
  cache:
    container_name: cache
    image: memcached
    ports:
      - "11211:11211"
    entrypoint:
      - memcached
      - -m 64
  app:
    container_name: app
    build:
        context: .
    command: > 
        sh -c "python manage.py makemigrations &&
               python manage.py migrate &&
               python manage.py collectstatic --noinput &&
               gunicorn tviterapp.wsgi:application --bind 0.0.0.0:8000"
    volumes:
      - .:/app
      - static_volume:/app/static
    ports:
      - "8000:8000"
    env_file:
      .env
    depends_on:
      - baza
      - cache
volumes:
  postgres_data:
  static_volume:
```

Također stvaramo i dva ugnježđena direktorija `/nginx/prod/` unutar kojih će se nalaziti datoteka `nginx.conf`:

``` shell
$ mkdir -p nginx/prod/
$ touch nginx/prod/nginx.conf
```

Sadržaj datoteke `nginx.conf` prikazan je ispod. Datoteka služi za konfiguriranje `nginx` servera koji će proxy-at zahtjeve te servirati statične datoteke.

``` conf
upstream projekt {
    server app:8000;
}
server {

    listen 80;

    location / {
        proxy_pass http://projekt;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_redirect off;
    }

    location /static/ {
        alias /app/static/;
    }
}
```

## Postavke Django aplikacije

U datoteci `settings.py` unutar direktorija `tviterapp` našeg Django projekta mijenjamo stavke `DEBUG`, `ALLOWED_HOSTS` i `DATABASES` da dohvaćaju vrijednosti iz varijabli okoline:

``` python
DEBUG = os.getenv('DEBUG')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS').split(' ')

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE'),
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USERNAME'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT')
    }
}
```

U `settings.py` dodajemo i slijedeće stavke - `CACHES` za postavljanje `Memcached` sustava i definiranje lokacije `STATIC_ROOT` za statične datoteke:

``` python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'cache:11211',
    }
}

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
```

Također, u datoteci `urls.py` unutar direktorija `main` našeg projekta postavljamo keširanje pogleda dodavanjem:

``` python
from django.views.decorators.cache import cache_page

urlpatterns = [
    path('tvitovi/', cache_page(60)(TvitoviList.as_view())) # cache-ira pogled 60 sekundi
]
```

## Izgradnja i pokretanje Docker kompozicije

Pull-amo potrebne slike:

``` shell
$ docker-compose pull
Pulling baza   ... done
Pulling cache  ... done
Pulling app    ... done
Pulling server ... done
```

Zatim podižemo kompoziciju:

``` shell
$ docker-compose up
```

U kontejneru Django aplikacije stvaramo superuser-a za prijavu u admin panel:

``` shell
$ sudo docker-compose exec app python manage.py createsuperuser
```

Sada u browser možemo upisati `localhost` i testirati postavu.
Kompoziciju zatim možemo *srušiti* na drugom terminalu:

``` shell
$ docker-compose down
Stopping server ... done
Stopping app    ... done
Stopping baza   ... done
Stopping cache  ... done
Removing server ... done
Removing app    ... done
Removing baza   ... done
Removing cache  ... done
Removing network django-tviter_default
```
