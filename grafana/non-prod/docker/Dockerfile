# Use the official Grafana image
FROM grafana/grafana:latest

# Install Python
USER root
RUN apk add --no-cache python3 py3-pip

# Copy provisioning and dashboards
COPY ./provisioning /etc/grafana/provisioning
COPY ./dashboards /var/lib/grafana/dashboards

# Copy the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Ensure the entrypoint script is executable
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose Grafana port
EXPOSE 3000

# Switch to the non-root user provided by the base image
USER grafana

# Uncomment and set environment variables for configuration if needed
# ENV GF_AUTH_ANONYMOUS_ENABLED=true 
# ENV GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer 
# ENV GF_AUTH_BASIC_ENABLED=false 
# ENV GF_AUTH_DISABLE_LOGIN_FORM=true 
# ENV GF_AUTH_DISABLE_SIGNOUT_MENU=true 
# ENV GF_SECURITY_ALLOW_EMBEDDING=true
# ENV GF_SERVER_SERVE_FROM_SUB_PATH=true  
# ENV GF_SERVE_FROM_SUB_PATH=true

# Set the entrypoint script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Set the default command
CMD ["grafana-server", "--homepath=/usr/share/grafana"]