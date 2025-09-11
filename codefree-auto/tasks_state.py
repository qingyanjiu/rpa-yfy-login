from typing import Dict

class TaskState:
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}

    def create_task(self, task_id, total):
        self.tasks[task_id] = {"total": total, "sent": 0, "status": "running"}

    def update_task(self, task_id, sent):
        if task_id in self.tasks:
            self.tasks[task_id]["sent"] = sent

    def finish_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "finished"

    def get_task(self, task_id):
        return self.tasks.get(task_id, None)