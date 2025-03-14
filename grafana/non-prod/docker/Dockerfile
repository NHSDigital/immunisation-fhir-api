# Use the official Grafana image
FROM grafana/grafana

# Add provisioning and dashboards
ADD ./provisioning /etc/grafana/provisioning
ADD ./dashboards /var/lib/grafana/dashboards

# Expose Grafana port
EXPOSE 3000

# Create a non-root user and group
RUN groupadd -r grafana && useradd -r -g grafana grafana

# Change ownership of the directories to the non-root user
RUN chown -R grafana:grafana /etc/grafana /var/lib/grafana

# Switch to the non-root user
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

# Set the default command
CMD [ "grafana-server", "--homepath=/usr/share/grafana" ]