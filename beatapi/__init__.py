import os

from celery import Celery
from quart import Quart

app = Quart(__name__)
app.config['PROCESSING_DIR'] = './beat-api-tmp'
app.config['RESULT_LIFETIME'] = 8 * 60
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
app.config['CELERY_BROKER_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])

from beatapi.v0 import api_v0
app.register_blueprint(api_v0)
