import json
import requests

class ChartCreator:
    def __init__(self, superset_url, auth_token):
        self.superset_url = superset_url
        self.auth_token = auth_token
        self.headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }

    def create_chart(self, chart_name, datasource_id, viz_type, params):
        url = f'{self.superset_url}/api/v1/chart/'
        payload = {
            'slice_name': chart_name,
            'viz_type': viz_type,
            'datasource_id': datasource_id,
            'params': json.dumps(params)
        }
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 201:
            return response.json()
        else:
            response.raise_for_status()

    def update_chart(self, chart_id, chart_name=None, params=None):
        url = f'{self.superset_url}/api/v1/chart/{chart_id}'
        payload = {}
        if chart_name:
            payload['slice_name'] = chart_name
        if params:
            payload['params'] = json.dumps(params)
        response = requests.put(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def delete_chart(self, chart_id):
        url = f'{self.superset_url}/api/v1/chart/{chart_id}'
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 200:
            return {'status': 'success', 'message': 'Chart deleted successfully'}
        else:
            response.raise_for_status()