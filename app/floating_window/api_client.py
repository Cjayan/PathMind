"""
api_client.py - HTTP client for communicating with the local Flask API.
"""
import json
import io
import urllib.request
import urllib.error
import urllib.parse


class ApiClient:
    """Lightweight HTTP client using stdlib only (no requests dependency)."""

    def __init__(self, base_url='http://127.0.0.1:5000'):
        self.base_url = base_url.rstrip('/')

    def set_port(self, port):
        self.base_url = f'http://127.0.0.1:{port}'

    # ── Public API ──

    def list_products(self):
        return self._get('/api/products/')

    def list_flows(self, product_id=None):
        url = '/api/flows/'
        if product_id:
            url += f'?product_id={product_id}'
        return self._get(url)

    def list_steps(self, flow_id):
        return self._get(f'/api/steps/?flow_id={flow_id}')

    def create_step(self, flow_id, description, image_bytes=None, score=None, notes=None):
        """Create a step via multipart form upload."""
        boundary = '----PythonFloatingWindowBoundary'
        body_parts = []

        def add_field(name, value):
            body_parts.append(
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f'{value}\r\n'
            )

        add_field('flow_id', str(flow_id))
        add_field('description', description or '')
        if score and score > 0:
            add_field('score', str(score))
        if notes:
            add_field('notes', notes)

        body_bytes = ''.join(body_parts).encode('utf-8')

        # Add image file part if provided
        if image_bytes:
            file_header = (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="image"; filename="screenshot.png"\r\n'
                f'Content-Type: image/png\r\n\r\n'
            ).encode('utf-8')
            file_footer = b'\r\n'
            body_bytes += file_header + image_bytes + file_footer

        body_bytes += f'--{boundary}--\r\n'.encode('utf-8')

        url = self.base_url + '/api/steps/'
        req = urllib.request.Request(
            url,
            data=body_bytes,
            method='POST',
            headers={
                'Content-Type': f'multipart/form-data; boundary={boundary}',
            }
        )
        return self._do_request(req)

    def get_flow(self, flow_id):
        return self._get(f'/api/flows/{flow_id}')

    def get_config(self):
        """Get application config."""
        return self._get('/api/config/')

    def trigger_ai_comment(self, step_id):
        """Trigger AI comment generation for a step.

        The server handles image loading, compression, and AI call internally.
        Uses a longer timeout (90s) since the server-side AI call may take ~60s.
        """
        return self._post_json('/api/ai/generate-step-comment', {'step_id': step_id}, timeout=90)

    def test_connection(self):
        """Test if the Flask server is reachable."""
        try:
            self._get('/api/products/')
            return True
        except Exception:
            return False

    # ── Internal ──

    def _get(self, path):
        url = self.base_url + path
        req = urllib.request.Request(url, method='GET')
        return self._do_request(req)

    def _post_json(self, path, data, timeout=30):
        """Send a JSON POST request."""
        url = self.base_url + path
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=body,
            method='POST',
            headers={'Content-Type': 'application/json'},
        )
        return self._do_request(req, timeout=timeout)

    def _do_request(self, req, timeout=30):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read().decode('utf-8')
                return json.loads(data)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            try:
                err = json.loads(body)
                msg = err.get('error', body[:200])
            except json.JSONDecodeError:
                msg = body[:200]
            raise RuntimeError(f'HTTP {e.code}: {msg}')
        except urllib.error.URLError as e:
            raise ConnectionError(f'无法连接到服务器: {e.reason}')
