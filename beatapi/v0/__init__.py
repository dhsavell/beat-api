import json
import os
import uuid
from http import HTTPStatus

import jsonschema
from quart import Blueprint, request, jsonify, Response, send_from_directory

from beatapi import app, limiter
from beatapi.tasks import processing_task, get_input_file_path

api_v0 = Blueprint('api_v0', __name__, url_prefix='/api/v0')

with open(os.path.join(app.root_path, 'schemas/submission.json'), 'r') as fp:
    submission_schema = json.load(fp)


def error(description: str, reason: str) -> Response:
    return jsonify({
        'error': description,
        'reason': reason
    })


def is_file_valid(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['mp3']


@api_v0.route(path='/submit', methods=['POST'])
@limiter.limit('1 per minute')
async def submit():
    form = await request.form

    if 'data' not in form:
        return error('no data supplied', 'missing "data" field in request'), HTTPStatus.BAD_REQUEST

    try:
        song_data = json.loads(form['data'])
    except json.JSONDecodeError as e:
        return error('invalid json', e.msg.lower()), HTTPStatus.BAD_REQUEST

    try:
        jsonschema.validate(song_data, submission_schema)
    except jsonschema.ValidationError as e:
        return error('schema validation failed', e.message), HTTPStatus.BAD_REQUEST

    files = await request.files

    if 'song' not in files:
        return error('invalid file', 'no file was provided'), HTTPStatus.BAD_REQUEST

    file = files['song']

    if not file or not file.filename.strip():
        return error('invalid file', 'no file was provided'), HTTPStatus.BAD_REQUEST

    if not is_file_valid(file.filename):
        return error('invalid file', 'unacceptable file. does it have a valid extension?'), HTTPStatus.BAD_REQUEST

    file_id = str(uuid.uuid4())
    input_path = get_input_file_path(file_id)
    file.save(input_path)

    try:
        task = processing_task.delay(file_id, song_data)
        return jsonify({
            'status': {
                'id': task.id,
                'method': 'get',
                'href': f'{api_v0.url_prefix}/status/{task.id}'
            }
        }), HTTPStatus.ACCEPTED
    except IOError:
        if os.path.isfile(input_path):
            os.remove(input_path)

        return error('internal server error', 'failed to save file -- try again shortly'), \
               HTTPStatus.INTERNAL_SERVER_ERROR


@api_v0.route(path='/status/<task_id>', methods=['GET'])
@limiter.exempt
async def status(task_id: str):
    task = processing_task.AsyncResult(task_id)

    if task.state == 'PROGRESS':
        return jsonify({
            'state': 'PROGRESS',
            'current_effect': task.info.get('current_effect', 0)
        }), HTTPStatus.OK
    elif task.state == 'SUCCESS':
        return Response(response='', status=HTTPStatus.SEE_OTHER, headers={
            'Location': f'{api_v0.url_prefix}/result/{task.get()}'
        })
    elif task.state == ' FAILURE':
        return jsonify({
            'state': 'FAILURE',
            'reason': str(task.result)
        }), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify({
        'state': task.state,
    }), HTTPStatus.OK


@api_v0.route(path='/result/<file_id>', methods=['GET'])
@limiter.exempt
async def result(file_id: str):
    return await send_from_directory(app.config['PROCESSING_DIR'], file_id + '.mp3')
