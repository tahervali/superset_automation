import requests

class SupersetAuth:
    def __init__(self, superset_url, username, password):
        self.superset_url = superset_url
        self.username = username
        self.password = password
        self.session = None
        self.headers = None
    
    def authenticate(self):
        """Authenticate with Superset and return session and headers"""
        print("🔐 Authenticating...")
        self.session = requests.Session()
        self.session.get(f"{self.superset_url}/login/")
        
        payload = {
            "username": self.username,
            "password": self.password,
            "provider": "db"
        }
        
        resp = self.session.post(f"{self.superset_url}/api/v1/security/login", json=payload)
        resp.raise_for_status()
        
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        csrf = self.session.get(f"{self.superset_url}/api/v1/security/csrf_token/", headers=headers)
        csrf.raise_for_status()
        
        self.headers = {
            "Authorization": f"Bearer {token}",
            "X-CSRFToken": csrf.json()["result"],
            "Content-Type": "application/json",
            "Referer": self.superset_url
        }
        
        print("✅ Authenticated")
        return self.session, self.headers
    
    def get_dataset_info(self, dataset_id):
        """Get dataset information including columns and metrics"""
        if not self.session or not self.headers:
            raise Exception("Not authenticated. Call authenticate() first.")
        
        resp = self.session.get(f"{self.superset_url}/api/v1/dataset/{dataset_id}", headers=self.headers)
        if resp.status_code != 200:
            print("❌ Failed to fetch dataset")
            return None
        
        data = resp.json()["result"]
        return {
            "columns": [c["column_name"] for c in data["columns"]],
            "metrics": [m["metric_name"] for m in data["metrics"]]
        }