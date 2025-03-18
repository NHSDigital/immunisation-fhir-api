# Use the official Nginx image
FROM nginx:alpine

# Debug statement to indicate the start of the build process
RUN echo "Starting the Docker build process..."

# Copy the HTML file into the Nginx web root
RUN echo "Copying index.html to /usr/share/nginx/html/index.html..."
COPY index.html /usr/share/nginx/html/index.html
RUN echo "index.html copied successfully."

# Expose port 80 to the outside world
RUN echo "Exposing port 80..."
EXPOSE 80

# Debug statement to indicate the end of the build process
RUN echo "Docker build process completed."