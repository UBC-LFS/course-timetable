# Course Scheduling Application

This project is a web-based Course organization application, which runs on Django with PostgreSQL.

### Features
- Filter Course sections for time conflict finding
- See past schedules of courses
- update and edit course times for easier course planning
- Shibboleth login technology

# Installation Guide

### Linux Container's Environment
- Ubuntu 22.04
- Python 3.10.6
- Django 4.2 or greater

### Install prerequisites for Ubuntu

#### 1. Install the latest stable version of Git first if it does not exist

```
# https://git-scm.com/download/linux
$ sudo apt install software-properties-common
$ sudo add-apt-repository ppa:git-core/ppa
$ sudo apt update
$ sudo apt install git
```

#### 2. Clone this repository

```
$ git clone https://github.com/UBC-LFS/course-timetable.git
```

#### 3. Install the python3 virtual environment and activate it

```
$ sudo apt update
$ sudo apt install python3-venv

$ python3 -m venv venv
$ source venv/bin/activate
```

#### 4. Install pip3

```
$ sudo apt update
$ sudo apt install python3-pip
$ pip3 install --upgrade pip
```

#### 5. Install requirements

```
$ cd ta-application-system
$ pip3 install -r requirements.txt

# errors might occur in some packages, then install the following packages
$ sudo apt-get install python3-setuptools python3-dev libxml2-dev libxmlsec1-dev libxmlsec1-openssl
```


## Summary of Deployment
0. Rename *timetable/settings.py.example* to *timetable/settings.py*

1. Clone this Github repository
```
$ git clone https://github.com/UBC-LFS/course-timetable.git
```

2. Install requirement dependencies
```
$ pip install -r requirements.txt
```

3. Set Environment Variables in your machine:
```
SECRET_KEY = os.environ.get('TIMETABLE_SECRET_KEY')
LDAP_URI = os.getenv('LDAP_URI')  # or 'ldaps://...' if using SSL
LDAP_DEFAULT_BIND_DN = os.getenv('LDAP_DEFAULT_BIND_DN')  # base DN for user lookup
LDAP_USER_SEARCH_BASE = os.getenv('LDAP_USER_SEARCH_BASE')  # base DN for user search
LDAP_PASSWORD = os.getenv('LDAP_PASSWORD')  # password for the default bind DN
LDAP_GROUP_SEARCH_BASE = os.getenv('LDAP_GROUP_SEARCH_BASE')  # base DN for group
LDAP_MEMBER_FILTER = os.getenv('LDAP_MEMBER_FILTER')  # filter to find members in a group
DATABASE_ENGINE = os.environ.get('TIMETABLE_DB_ENGINE'),
DATABASE_NAME = os.environ.get('TIMETABLE_DB_NAME'),
DATABASE_USER = os.environ.get('TIMETABLE_DB_USER'),
DATABASE_PASSWORD = os.environ.get('TIMETABLE_DB_PASSWORD'),
DATABASE_HOST =  os.environ.get('TIMETABLE_DB_HOST'),
DATABASE_PORT = os.environ.get('TIMETABLE_DB_PORT')
```

4. Switch *DEBUG* to **False** in a *settings.py* file
```
DEBUG = False
```

5. Add a Media root directory to store certificate files
```
MEDIA_ROOT = 'your_media_root'
```

6. Add your allowed_hosts in *settings.py*
```
ALLOWED_HOSTS = ['YOUR_HOST']
```

7. Create staticfiles in your directory
```
$ python manage.py collectstatic --noinput

# References
# https://docs.djangoproject.com/en/2.2/howto/static-files/
# https://devcenter.heroku.com/articles/django-assets
# https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Deployment
```

8. Create a database in Postgresql

9. Create database tables, and migrate
```
$ python manage.py migrate
```

10. Load data for local testing
```
$ python manage.py loaddata timetable/fixtures/*.json
```

12. See a deployment checklist and change your settings
```
$ python manage.py check --deploy


# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# SECURE_SSL_REDIRECT = True
# X_FRAME_OPTIONS = 'DENY'
```

13. Now, it's good to go. Run this web application in your production!
```
$ python manage.py runserver
```

14. Timezone in settings.py
https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

```
# Choose the timezone where you live
TIME_ZONE = 'America/Vancouver'
```

## Login locally
1. Create a superuser
```
# Reference: https://docs.djangoproject.com/en/2.2/topics/auth/default/
$ python manage.py createsuperuser --username=joe --email=joe@example.com
```

2. Run this app
```
$ python manage.py runserver

For scheduling tasks
$ python manage.py runserver --noreload

```


**Upgrade Django**
```
pip install --upgrade django==new_version (e.g., 2.2.19)
```

Enjoy :)
