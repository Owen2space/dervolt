"""
Scheduler for periodic tasks in the Der-Volt application.
This module sets up scheduled tasks like daily forex rate updates.
"""

import logging
from datetime import datetime
import threading
import time

# Configure logging
logger = logging.getLogger(__name__)

# Try to import APScheduler, but provide a fallback if it's not available
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_APSCHEDULER = True
    logger.info("Using APScheduler for task scheduling")
except ImportError:
    HAS_APSCHEDULER = False
    logger.warning("APScheduler not available, using fallback thread-based scheduler")

import forex_utils

# Create scheduler instance if APScheduler is available
if HAS_APSCHEDULER:
    scheduler = BackgroundScheduler()
else:
    scheduler = None
    # Thread reference for fallback scheduler
    scheduler_thread = None

def update_forex_rates():
    """
    Task to update forex rates from CurrencyLayer API.
    This will be scheduled to run once per day.
    """
    logger.info(f"Running scheduled forex rate update at {datetime.now()}")
    try:
        # Fetch the latest rates
        rate = forex_utils.fetch_forex_rate()
        if rate:
            logger.info(f"Successfully updated forex rate: {rate}")
        else:
            logger.error("Failed to update forex rate")
    except Exception as e:
        logger.error(f"Error in scheduled forex rate update: {e}")

def fallback_scheduler():
    """
    Fallback thread-based scheduler that runs when APScheduler is not available.
    Updates forex rates once a day (every 86400 seconds).
    """
    logger.info("Starting fallback thread-based scheduler")
    
    # Run update immediately on startup
    update_forex_rates()
    
    # Then run daily
    while True:
        # Sleep for 1 day (86400 seconds)
        time.sleep(86400)
        try:
            update_forex_rates()
        except Exception as e:
            logger.error(f"Error in fallback scheduler: {e}")

def init_scheduler():
    """
    Initialize and start the scheduler with all scheduled tasks.
    """
    global scheduler_thread
    
    if HAS_APSCHEDULER and scheduler:
        # Schedule the forex rate update to run daily at 00:05 UTC
        # This time is chosen because forex markets typically reset at midnight
        scheduler.add_job(
            update_forex_rates,
            trigger=CronTrigger(hour=0, minute=5),
            id='update_forex_rates',
            name='Update forex rates daily',
            replace_existing=True
        )
        
        # Run once at startup to ensure we have the latest rates
        scheduler.add_job(
            update_forex_rates, 
            id='update_forex_rates_startup',
            name='Update forex rates at startup'
        )
        
        # Start the scheduler
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started - forex rates will update daily at 00:05 UTC")
        else:
            logger.info("Scheduler already running")
        
        return scheduler
    else:
        # Use fallback thread-based scheduler
        logger.info("Using fallback thread-based scheduler")
        scheduler_thread = threading.Thread(target=fallback_scheduler, daemon=True)
        scheduler_thread.start()
        return scheduler_thread

def shutdown_scheduler():
    """
    Shutdown the scheduler when the application stops.
    """
    if HAS_APSCHEDULER and scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shutdown")
    else:
        # No need to explicitly shutdown daemon threads
        logger.info("No APScheduler instance to shutdown") 