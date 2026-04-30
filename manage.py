#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import sys
import io
import os
import logging

# 1. Replace stdout/stderr with UTF-8 wrappers
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 2. Force reconfigure the root logger to use the new stdout
logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO,
    force=True   # This is the magic – overrides any existing configuration
)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()