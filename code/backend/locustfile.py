"""
Load Testing for Research Copilot

Uses Locust to simulate user load and measure system performance.
"""

import json
import time
from typing import Dict, Any

from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import print_stats


class ResearchCopilotUser(HttpUser):
    """Simulates a research copilot user."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_token = None
        self.api_key = None

    def on_start(self):
        """Setup user session."""
        self.login()

    def login(self):
        """Authenticate user and get token."""
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }

        with self.client.post("/api/v1/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                if self.auth_token:
                    self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
            else:
                # If login fails, continue without auth for public endpoints
                pass

    @task(3)  # Higher weight - common operation
    def health_check(self):
        """Test health check endpoint."""
        self.client.get("/health")

    @task(2)
    def ping(self):
        """Test ping endpoint."""
        self.client.get("/ping")

    @task(1)
    def api_ping(self):
        """Test API ping endpoint."""
        self.client.get("/api/v1/ping")

    @task(5)  # Most common operation
    def search_papers(self):
        """Test paper search functionality."""
        search_queries = [
            "machine learning",
            "artificial intelligence",
            "deep learning",
            "neural networks",
            "computer vision",
            "natural language processing",
            "reinforcement learning",
            "supervised learning"
        ]

        import random
        query = random.choice(search_queries)

        search_data = {
            "query": query,
            "search_type": "hybrid",
            "top_k": 10
        }

        with self.client.post("/api/v1/search", json=search_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                # Validate response structure
                if "results" in data and isinstance(data["results"], list):
                    response.success()
                else:
                    response.failure("Invalid search response structure")
            elif response.status_code == 401:
                # Re-authenticate if token expired
                self.login()
            else:
                response.failure(f"Search failed with status {response.status_code}")

    @task(4)
    def rag_query(self):
        """Test RAG question answering."""
        questions = [
            "What is machine learning?",
            "How does deep learning work?",
            "What are neural networks?",
            "Explain artificial intelligence",
            "What is supervised learning?",
            "How does reinforcement learning work?"
        ]

        import random
        question = random.choice(questions)

        rag_data = {
            "query": question,
            "top_k": 5,
            "include_sources": True
        }

        with self.client.post("/api/v1/rag/ask", json=rag_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "answer" in data and "sources" in data:
                    response.success()
                else:
                    response.failure("Invalid RAG response structure")
            elif response.status_code == 401:
                self.login()
            else:
                response.failure(f"RAG query failed with status {response.status_code}")

    @task(2)
    def browse_papers(self):
        """Test paper browsing and retrieval."""
        # First get some papers
        with self.client.get("/api/v1/papers?limit=20", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "papers" in data and data["papers"]:
                    # Pick a random paper to view details
                    import random
                    paper = random.choice(data["papers"])
                    paper_id = paper.get("id")

                    if paper_id:
                        # Get paper details
                        self.client.get(f"/api/v1/papers/{paper_id}")
                response.success()
            elif response.status_code == 401:
                self.login()
            else:
                response.failure(f"Paper browsing failed with status {response.status_code}")

    @task(1)
    def user_profile(self):
        """Test user profile access."""
        with self.client.get("/api/v1/users/me", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "email" in data:
                    response.success()
                else:
                    response.failure("Invalid user profile response")
            elif response.status_code == 401:
                self.login()
            else:
                response.failure(f"Profile access failed with status {response.status_code}")

    @task(1)
    def data_ingestion_status(self):
        """Test data ingestion status checking."""
        self.client.get("/api/v1/ingestion/status")

    @task(1)
    def analytics_data(self):
        """Test analytics data access."""
        with self.client.get("/api/v1/analytics/overview", catch_response=True) as response:
            if response.status_code in [200, 401, 403]:
                response.success()
            else:
                response.failure(f"Analytics access failed with status {response.status_code}")


class AdminUser(HttpUser):
    """Simulates an admin user with elevated permissions."""

    wait_time = between(2, 5)

    def on_start(self):
        """Setup admin session."""
        self.login_admin()

    def login_admin(self):
        """Login as admin user."""
        login_data = {
            "email": "admin@example.com",
            "password": "adminpassword123"
        }

        with self.client.post("/api/v1/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                if self.auth_token:
                    self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})

    @task(2)
    def admin_user_management(self):
        """Test admin user management."""
        with self.client.get("/api/v1/admin/users", catch_response=True) as response:
            if response.status_code in [200, 401, 403]:
                response.success()
            else:
                response.failure(f"Admin user management failed with status {response.status_code}")

    @task(1)
    def admin_system_metrics(self):
        """Test admin system metrics access."""
        self.client.get("/api/v1/admin/metrics")

    @task(1)
    def admin_audit_logs(self):
        """Test admin audit log access."""
        self.client.get("/api/v1/admin/audit")


class APIKeyUser(HttpUser):
    """Simulates a user using API keys instead of JWT tokens."""

    wait_time = between(1, 2)

    def on_start(self):
        """Setup API key authentication."""
        self.client.headers.update({"X-API-Key": "test_api_key_123"})

    @task(3)
    def api_key_search(self):
        """Test search with API key auth."""
        search_data = {
            "query": "machine learning",
            "search_type": "bm25",
            "top_k": 5
        }

        self.client.post("/api/v1/search", json=search_data)

    @task(2)
    def api_key_rag(self):
        """Test RAG with API key auth."""
        rag_data = {
            "query": "What is AI?",
            "top_k": 3
        }

        self.client.post("/api/v1/rag/ask", json=rag_data)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when a load test starts."""
    print("🚀 Starting Research Copilot load test")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when a load test stops."""
    print("🛑 Load test completed")
    print_stats(environment.stats)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response,
               context, exception, start_time, url, **kwargs):
    """Called for each request."""
    if exception:
        print(f"❌ Request failed: {name} - {exception}")
    elif response and response.status_code >= 400:
        print(f"⚠️  Request error: {name} - Status {response.status_code}")


# Custom metrics and monitoring
@events.request.add_listener
def record_custom_metrics(request_type, name, response_time, response_length, response,
                         context, exception, start_time, url, **kwargs):
    """Record custom performance metrics."""
    if response and hasattr(response, 'headers'):
        # Track rate limiting
        if response.status_code == 429:
            print(f"🚦 Rate limited: {name}")

        # Track server response times
        if response_time > 5000:  # 5 seconds
            print(f"🐌 Slow response: {name} - {response_time}ms")

        # Track memory usage if available
        server_timing = response.headers.get('server-timing')
        if server_timing:
            print(f"⏱️  Server timing: {server_timing}")


if __name__ == "__main__":
    # Allow running locust directly for debugging
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        # Debug mode - run a single user
        env = Environment(user_classes=[ResearchCopilotUser])
        env.create_local_runner()

        # Run for 10 seconds
        env.runner.start(1, spawn_rate=1)
        time.sleep(10)
        env.runner.stop()

        print_stats(env.stats)
    else:
        # Normal locust execution
        from locust.main import main
        main()