#!/usr/bin/env bash

#!/bin/bash
# Start Django app using gunicorn
# Listen on the port Render provides via $PORT
exec gunicorn background_remover_project.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 2 \
    --timeout 120