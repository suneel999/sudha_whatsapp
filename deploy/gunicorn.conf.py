# Production gunicorn config for Sudha WhatsApp bot
bind = "127.0.0.1:8000"
workers = 1
threads = 4
timeout = 60
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = "info"
# Single worker avoids duplicate webhook processing with in-memory session caches
