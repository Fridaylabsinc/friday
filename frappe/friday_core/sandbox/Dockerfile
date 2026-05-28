# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

FROM python:3.14-slim AS runtime

# ---------------------------------------------------------------
# Dependencies — pinned for reproducibility
# ---------------------------------------------------------------
RUN pip install --no-cache-dir \
    requests==2.32.3 \
    pydantic==2.7.1 \
    frappe-client==1.0.0

# ---------------------------------------------------------------
# Nonroot user (matches UID 65532 used by runner.py)
# ---------------------------------------------------------------
RUN useradd --no-create-home --uid 65532 friday
USER friday
WORKDIR /home/friday

# ---------------------------------------------------------------
# Entrypoint — reads task JSON from stdin, exits with result
# ---------------------------------------------------------------
COPY --chown=friday:friday entrypoint.py /home/friday/entrypoint.py
COPY --chown=friday:friday handlers.py /home/friday/handlers.py
ENTRYPOINT ["python", "/home/friday/entrypoint.py"]
