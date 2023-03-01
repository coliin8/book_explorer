from celery import shared_task, Task
import requests


class BaseTaskWithRetry(Task):
    autoretry_for = (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
    retry_kwargs = {"max_retries": 25}
    retry_backoff = 5
    retry_jitter = (True,)


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_process_notification(self, s3_url):
    requests.post(
        "https://postman-echo.com/post",
        data=s3_url.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
    )
