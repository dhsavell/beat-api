web: celery worker -A beatapi.celery & hypercorn -b 0.0.0.0:${PORT} beatapi:app & wait -n
