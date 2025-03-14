# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application files into the container
COPY . .

# Create a simple Python script to serve "Hello, World!"
RUN echo 'from http.server import SimpleHTTPRequestHandler, HTTPServer\n\
class Handler(SimpleHTTPRequestHandler):\n\
    def do_GET(self):\n\
        self.send_response(200)\n\
        self.send_header("Content-type", "text/plain")\n\
        self.end_headers()\n\
        self.wfile.write(b"Hello, World!")\n\
\n\
if __name__ == "__main__":\n\
    server = HTTPServer(("0.0.0.0", 8000), Handler)\n\
    print("Starting server on port 8000")\n\
    server.serve_forever()' > server.py

# Expose port 8000 to the outside world
EXPOSE 8000

# Run the Python script
CMD ["python", "server.py"]