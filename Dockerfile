# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/
ARG PYTHON_VERSION=3.12.0
FROM python:${PYTHON_VERSION}-slim as base
WORKDIR /app

# Create a non-privileged user that the src will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser --disabled-password --gecos "" --home "/nonexistent" --shell "/sbin/nologin" --no-create-home --uid "${UID}" appuser

# Setup flags and Install the venv
ENV PYTHONDONTWRITEBYTECODE=1 
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app"

#ENV VIRTUAL_ENV=/opt/venv
#RUN python3 -m venv $VIRTUAL_ENV
#ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
COPY /conf/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip --mount=type=bind,source=./conf/requirements.txt,target=requirements.txt python -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application.
# USER appuser

# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on && Run the application
LABEL version="0.0.1"
LABEL description="Riot API"

EXPOSE 8000 
EXPOSE 8001
CMD uvicorn src.backend.riotapi.riotapi:app --host=0.0.0.0 --port=8001
