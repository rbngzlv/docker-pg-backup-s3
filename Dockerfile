FROM python:3.11-slim-bullseye

RUN ln -snf /usr/share/zoneinfo/UTC /etc/localtime \
    && echo UTC > /etc/timezone

# Create default user and home directory, set owner
RUN (getent group 2001 || addgroup --system --gid 2001 backups) \
    && (getent passwd 2001 || adduser --system backups --shell /bin/bash --uid 2001 --ingroup `getent group 2001 | cut -d: -f1`)

RUN set -ex \
    && apt update -q \
    && DEBIAN_FRONTEND=noninteractive apt install -yq --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        postgresql-common \
        vim \
    && sh /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
    && DEBIAN_FRONTEND=noninteractive apt install -yq --no-install-recommends \
        postgresql-client-15 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/backups

COPY --chown=2001:2001 requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY --chown=2001:2001 . .

ENTRYPOINT [ "sh", "entrypoint.sh" ]

USER 2001

CMD []
