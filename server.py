import http.server
import socketserver
import json
import urllib.request
import os

PORT = 3000
DIRECTORY = "."

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

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
