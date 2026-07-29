import http.server
import socketserver
import json
import urllib.request
import os

import news_feed

PORT = 3000
DIRECTORY = "."

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Headlines for the morning dashboard. Fetched here rather than in the
        # browser because news RSS feeds don't send CORS headers.
        if self.path.split('?')[0] == '/api/news':
            try:
                self._send_json(news_feed.get_headlines())
            except Exception as e:
                print("Failed to load headlines:", e)
                self._send_json({'status': 'error', 'message': str(e)}, status=502)
            return
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/sync':
            print("Syncing posts from Supabase...")
            url = 'https://pddrwxvauofsnchcmodn.supabase.co/rest/v1/posts?select=*&status=eq.published&order=published_at.desc'
            headers = {
                'apikey': 'sb_publishable_w_x9uuDPvOxYBpEr8Q4k6Q_ZHNAbMuX',
                'Authorization': 'Bearer sb_publishable_w_x9uuDPvOxYBpEr8Q4k6Q_ZHNAbMuX'
            }
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req) as response:
                    data = response.read()
                    # Write to posts.json
                    with open('posts.json', 'wb') as f:
                        f.write(data)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status": "success", "message": "Written to posts.json"}')
                    print("Successfully updated posts.json")
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Failed"}')
                print("Failed to sync:", e)
        else:
            self.send_response(404)
            self.end_headers()

with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
    print(f"Serving at port {PORT}")
    print(f"To sync posts, the admin panel will automatically send a POST request to http://localhost:{PORT}/api/sync")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
