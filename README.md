# emarches
emarches is a Python-based full-stack application aiming to provide a better alternative to the Moroccan Public Procurement portal.   
To see it in action, you can visit our deployed website at www.emarches.com

# Legal ?
Always remember: scraping may be illegal or cause you to be banned or blacklisted.
Before scraping any website, please make sure the owner of the website allows it.

# Docker ?
This application uses Chromium web browser and relies on Cron jobs to update database frequently. It is not pretty practical to run it in docker containers.

# Scraping a different website ?
This won't probably work out of the box. Because scraping depends on the target website structure and how it serves content ...

# How to test ?
1. Clone the repo, extract and cd...
2. Make a python virtual environment and install dependencies from both 'requirements.txt' and 'scraper/requirements.txt'.
3. Setup your .env files by removing 'example' from 'exammple.env', 'scraper/example.env', 'scraper/example.env.creds.json' and 'scraper/example.env.ua.json'. Change the values in theses files according to your setup.
4. Make migrations 'python manage.py makemigrations' and migrate 'python manage.py migrate'.
5. For scraping, run 'scraper/worker.py' with appropriate arguments. See 'argparse.ArgumentParser()' in 'constants.py' for the list of supported arguments.
6. To run the backend application, use 'python manage.py runserver' command.

# Production notes
1. For scraping automation, use the shell script and the service file included in 'scraper/crony'.
2. For backend application, use runserver as a standard Django application.

# .env files
1. .env:
    SITE_ROOT = "https://www.xxx.tld/" # Target website constants
    SITE_INDEX = "https://www.xxx.tld/index.php"
    LINK_PREFIX = 'https://www.xxx.tld/index.php?page=yyy&zzz='
    LINK_STITCH = '&aaa='

    DB_SERVER = '0.0.0.0' # Postgresql Database engine
    DB_PORT = 9999
    DB_NAME = "dbname"
    DB_USER = "dbuser"
    DB_PASS = "$trongP@ssw0rd-999"

    MEDIA_ROOT  = '/some/path/to/media' # Preferably absolute paths. Make sure they exist and are writeable.
    SELENO_DIR = '/some/main/path'

2. .env.creds.json: # Credentials to use to download DCE files. Use as many as possible. They are randomly shuffled.
    [
        {"fname": "John", "lname": "Doe", "email": "john@doe"},
        ...
        {"fname": "Jean", "lname": "Dupont", "email": "jean@dupont"}
    ]

3. .env.ua.json: # User-agents strings to use to navigate the target website. Use as many as possible. DO NOT include modile devices. They are randomly shuffled.
    [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
        ...
        "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    ]
