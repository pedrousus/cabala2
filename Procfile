release: python manage.py makemigrations
release: python manage.py migrate
release: python manage.py collectstatic --noinput
web: gunicorn traslateapi.wsgi:application --bind 0.0.0.0:$PORT