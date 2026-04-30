"""
Start Celery Worker and Beat Scheduler for 24/7 Automation

This script starts the Celery worker and beat scheduler to run scraping tasks
and send alerts automatically.

Usage:
    python start_celery.py

Requirements:
- Redis must be running (redis-server)
- Virtual environment activated
"""
import os
import sys
import subprocess
import time
import threading
import threading

def start_celery_worker():
    """Start Celery worker in a separate thread"""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_dir, 'venv', 'Scripts', 'python.exe')
    
    cmd = [
        venv_python, '-m', 'celery',
        '-A', 'config.celery',
        'worker',
        '--loglevel=info',
        '--concurrency=2',
        '--pool=solo'
    ]
    
    print("Starting Celery Worker...")
    subprocess.run(cmd)

def start_celery_beat():
    """Start Celery beat scheduler in a separate thread"""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_dir, 'venv', 'Scripts', 'python.exe')
    
    cmd = [
        venv_python, '-m', 'celery',
        '-A', 'config.celery',
        'beat',
        '--loglevel=info'
    ]
    
    print("Starting Celery Beat Scheduler...")
    subprocess.run(cmd)

def start_celery():
    """Start Celery worker and beat scheduler"""

    # Ensure we're in the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    # Activate virtual environment
    venv_python = os.path.join(project_dir, 'venv', 'Scripts', 'python.exe')
    if not os.path.exists(venv_python):
        print("❌ Virtual environment not found at venv/Scripts/python.exe")
        return

    print("🚀 Starting Celery Worker and Beat Scheduler...")
    print("This will run scraping tasks automatically 24/7")
    print("Press Ctrl+C to stop both services")

    try:
        # Start worker and beat in separate threads
        worker_thread = threading.Thread(target=start_celery_worker)
        beat_thread = threading.Thread(target=start_celery_beat)
        
        worker_thread.start()
        beat_thread.start()
        
        # Wait for both to finish
        worker_thread.join()
        beat_thread.join()

    except KeyboardInterrupt:
        print("\n🛑 Celery stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    start_celery()