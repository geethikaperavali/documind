import http.server
import socketserver
import sys

class RedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Redirecting to DocuMind...</title>
  <script>
    var target = 'http://localhost:8000' + window.location.pathname + window.location.search + window.location.hash;
    window.location.replace(target);
  </script>
</head>
<body style="font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#f8fafc;color:#0f172a;">
  <p>Connecting to DocuMind on port 8000...</p>
</body>
</html>"""
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    try:
        with socketserver.TCPServer(("", 3000), RedirectHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        sys.exit(0)
