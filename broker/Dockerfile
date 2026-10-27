FROM eclipse-mosquitto:2.0.22
# Configuration is baked into the image (no host bind mounts): the same image
# runs identically on any Docker host.
COPY --chown=1883:1883 mosquitto.conf acl /mosquitto/config/
COPY init-secrets.sh /usr/local/bin/init-secrets.sh
RUN chmod 0444 /mosquitto/config/mosquitto.conf \
 && chmod 0400 /mosquitto/config/acl \
 && chmod 0555 /usr/local/bin/init-secrets.sh
USER 1883:1883
