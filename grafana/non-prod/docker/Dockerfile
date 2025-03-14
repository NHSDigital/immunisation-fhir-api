# Use the official Nginx image from the Docker Hub
FROM nginx:alpine

# Copy the HTML file into the Nginx web root
COPY index.html /usr/share/nginx/html/index.html

# Expose port 80 to the outside world
EXPOSE 80

# No need to specify CMD as the base image already has the default command to run Nginx