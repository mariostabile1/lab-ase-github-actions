from locust import HttpUser, between, task

ADD = {"type": "add", "arguments": [2, 3]}
UPPER = {"type": "upper", "arguments": ["hello"]}


class ApiUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.client.post("/operations", json=ADD)

    @task(3)
    def add(self):
        self.client.post("/operations", json=ADD)

    @task(3)
    def upper(self):
        self.client.post("/operations", json=UPPER)

    @task(1)
    def last(self):
        self.client.get("/operations/last")
