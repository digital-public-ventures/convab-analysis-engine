"""Application package initialization."""

from app.csv_limits import configure_csv_field_limit

# Apply CSV parser safety defaults as soon as the app package is imported.
configure_csv_field_limit()
