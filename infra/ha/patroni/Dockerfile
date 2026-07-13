# Patroni + etcd production node (§20 / HA.md)
FROM postgres:16-alpine
RUN apk add --no-cache py3-pip py3-psycopg2 curl && \
    pip3 install --break-system-packages 'patroni[etcd3]==3.3.2' || \
    pip3 install 'patroni[etcd3]==3.3.2'
COPY primary.yml /etc/patroni/patroni.yml
ENV PATRONI_CONFIG_FILE=/etc/patroni/patroni.yml
EXPOSE 5432 8008
CMD ["patroni", "/etc/patroni/patroni.yml"]
