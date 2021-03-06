# ActiveTeachingModel

Note: All commands are given based on the assumption of using the Homebrew's package manager (MacOs).
Small changes are expected under Linux and/or Windows.

## Minimal configuration

#### Python 3

    brew install python3

#### Python libraries

* numpy, matplotlib, scipy

        pip3 install numpy matplotlib scipy

## Complete configuration

### Dependencies

#### Python 3

    brew install python3

#### Python libraries

* numpy, matplotlib, scipy
* gensim
* keras
* django, psycopg2-binary
* pillow

        pip3 install numpy matplotlib scipy gensim keras django psycopg2-binary pillow

#### PostgreSQL

Install postgresql (all commands are given considering the application running under MacOs)
Please refer to the documentation for details: https://www.postgresql.org/docs/9.1/creating-cluster.html 

    brew install postgresql

Run pgsql server (to have launchd start postgresql now and restart at login):

    brew services start postgresql

OR if you don't want/need a background service:

    pg_ctl -D /usr/local/var/postgres start

#### Pre-trained word2vec network

* Download at url: https://drive.google.com/file/d/0B7XkCwpI5KDYNlNUTTlSS21pQmM/edit
* Move the .bin in the folder 'word2vec/data'


### Prepare database

Create user and db

    createuser postgres
    createdb ActiveTeaching --owner postgres


### Initialize Django

Prepare the DB (make migrations and migrate)

    python3 manage.py makemigrations admin auth contenttypes sessions task

    python3 manage.py migrate

Optional: Create superuser in order to have access to admin interface

    python3 manage.py createsuperuser

### Import Kanji data

Import kanji data in db

    python3 db_fill_kanji_table.py

### Import user data

Load user data

    python3 db_user_data_load.py

### Run scripts


Analyse experimental results

    python3 data_analysis.py


Check quality of model by fitting the model to itself

    python3 model_evalulation.py


### Other operations

## Run Django server

Use the (classic) Django command

    python3 manage.py runserver

## Manipulations of DB

Backup user data

    python3 db_user_data_dump.py

...can be also done by dumping data using pg commands:

    pg_dump --data-only  --table question --table user ActiveTeaching --inserts > data/user_and_question_tables.sql


Remove the db

    dropdb ActiveTeaching


## PostgreSQL error management

In case database creation fails because of denied permissions in GNU/Linux refer to https://www.postgresql.org/docs/9.1/creating-cluster.html:
   
    root# mkdir /usr/local/pgsql
    root# chown postgres /usr/local/pgsql
    root# su postgres
    postgres$ initdb -D /usr/local/pgsql/data

Be sure that posgre sever is running

    brew services start postgre

In case error 'psycopg2.OperationalError: could not connect to server: No such file or directory
	Is the server running locally and accepting
	connections on Unix domain socket "/tmp/.s.PGSQL.5432"?' appears while the server is running:

    rm /usr/local/var/postgres/postmaster.pid

In case of troubles with permissions

    $ psql ActiveTeaching postgres
    ActiveTeaching=> \du

In case the user does not have enough privileges:

    ALTER ROLE role_name WITH SUPERUSER;

## Documentation

Auto-documentation is handled by Sphinx. In order to make changes:

1. Modify index.rst to change the main documentation page if needed. In addition, code.rst will be used to build the auto-documentation page if updated with the name of the script file as in:

```
    .. automodule:: learner.carlos_ann
    :members:
```

2. In the terminal, navigate to /docs and run:
    make html

If the build is successful the html files were updated at /docs/_build/html. Open index.html to start navigating the documentation pages.

More options and full documentation available at https://www.sphinx-doc.org/en/master/

## Sources

### Kanji database

   Coming from Tamaoka, K., Makioka, S., Sanders, S. & Verdonschot, R.G. (2017).
www.kanjidatabase.com: a new interactive online database for psychological and linguistic research on Japanese kanji
and their compound words. Psychological Research, 81, 696-708.
