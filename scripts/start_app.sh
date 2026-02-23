#!/bin/bash

echo "Applying database migrations..."
alembic -c alembic.ini upgrade head

python -m wakatime_tracker.main
