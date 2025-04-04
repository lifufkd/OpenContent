from celery_worker.worker import celery_app
from api.repository.heroes import delete_pending_heroes, delete_rejected_heroes


@celery_app.task
async def clean_pending_application():
    await delete_pending_heroes()


@celery_app.task
async def clean_rejected_application():
    await delete_rejected_heroes()
