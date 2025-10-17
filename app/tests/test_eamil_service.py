import asyncio
import time
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from celery.result import AsyncResult
from app.workers.tasks.email_service_task import send_email_task

load_dotenv()

user_list = ['techio.com.ng@gmail.com']

# Load email template
env = Environment(loader=FileSystemLoader('../../template'))
template = env.get_template('email_template.html')

email_context = {
    'subject': "Your Weekly Project Update",
    'title': "Project Phoenix: Status Report",
    'name': "Alex",
    'content': """
        <p>This is your weekly update for <strong>Project Phoenix</strong>.</p>
        <p>We've successfully completed the deployment of the new microservice. User feedback has been positive, and system metrics are stable.</p>
    """,
    'cta_text': "View Dashboard",
    'cta_link': "#"
}

html_output = template.render(email_context)

async def task1():
    print("Starting task1 queue...")
    for _ in range(10):
        task = send_email_task.delay(user_list, subject="Hello from task1!", html_body=html_output)
        print(f"Queued task1 job ID: {task.id}")
    print("Task1 jobs queued!")


async def task2():
    print("Starting task2 queue...")
    for _ in range(10):
        task = send_email_task.delay(user_list, subject="Hello from task2!", html_body=html_output)
        print(f"Queued task2 job ID: {task.id}")
    print("Task2 jobs queued!")


async def main():
    await asyncio.gather(task1(), task2())

    # Optionally check the last task’s result
    task = send_email_task.delay(user_list, subject="Status Check", html_body=html_output)
    result = AsyncResult(task.id)

    while result.status not in ["SUCCESS", "FAILURE"]:
        print(f"Waiting for task {task.id}... current status: {result.status}")
        time.sleep(2)
        result = AsyncResult(task.id)

    print("Final Status:", result.status)
    print("Result:", result.result)


if __name__ == "__main__":
    asyncio.run(main())
