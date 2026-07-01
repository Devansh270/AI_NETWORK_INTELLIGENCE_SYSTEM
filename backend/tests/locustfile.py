from locust import HttpUser, task, between


class DashboardUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def get_health(self):
        self.client.get("/health")

    @task(2)
    def get_summary(self):
        self.client.get("/metrics/summary")

    @task(1)
    def get_alerts(self):
        self.client.get("/alerts")
