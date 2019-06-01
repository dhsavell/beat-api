import quart.flask_patch  # noqa

import os

from celery import Celery
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from quart import Quart
from quart_cors import cors

app = cors(Quart(__name__))
app.config['PROCESSING_DIR'] = './beat-api-tmp'

if not os.path.isdir(app.config['PROCESSING_DIR']):
    os.mkdir(app.config['PROCESSING_DIR'])

app.config['RESULT_LIFETIME'] = 8 * 60
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
app.config['CELERY_BROKER_URL'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

limiter = Limiter(app, key_func=get_remote_address, default_limits=['1 per minute'])
celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])

from beatapi.v0 import api_v0

app.register_blueprint(api_v0)
