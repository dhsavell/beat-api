import os

from beatmachine.effect_loader import load_all_effects
from beatmachine.processor import load_as_beats
from beatmachine.effects import *
from celery import Task

from beatapi import celery, app


def get_input_file_path(file_id):
    return os.path.join(app.config['PROCESSING_DIR'], file_id + '-original' + '.mp3')


def get_output_file_path(file_id):
    return os.path.join(app.config['PROCESSING_DIR'], file_id + '.mp3')


@celery.task(bind=True)
def processing_task(self: Task, file_id: str, data: dict):
    input_path = get_input_file_path(file_id)
    result_path = get_output_file_path(file_id)

    try:
        effects = load_all_effects(data)

        self.update_state(state='PROGRESS', meta={'stage': 'loading_beats'})
        beats = load_as_beats(input_path)

        for i, effect in enumerate(effects):
            self.update_state(state='PROGRESS', meta={'stage': 'applying_effects', 'current_effect': i})
            beats = list(effect(beats))

        result = sum(beats)
        result.export(result_path)

        return file_id
    finally:
        os.remove(input_path)
        if os.path.isfile(result_path):
            cleanup_task.apply_async(args=[result_path], countdown=app.config['RESULT_LIFETIME'])


@celery.task()
def cleanup_task(path: str):
    if os.path.isfile(path):
        os.remove(path)
