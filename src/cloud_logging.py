"""Google Cloud Logging integration."""

import logging
import os

def setup_cloud_logging():
    """Configure Google Cloud Logging if running on GCP."""
    # Check if we are running in a GCP environment (App Engine or Cloud Run)
    is_gcp = os.environ.get('GAE_ENV') == 'standard' or os.environ.get('K_SERVICE')
    
    if is_gcp:
        try:
            import google.cloud.logging
            from google.cloud.logging.handlers import CloudLoggingHandler
            
            client = google.cloud.logging.Client()
            handler = CloudLoggingHandler(client)
            
            # Setup root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(handler)
            
            logging.info("Google Cloud Logging successfully configured.")
        except ImportError:
            logging.warning("google-cloud-logging not installed. Falling back to standard logging.")
        except Exception as e:
            logging.error(f"Failed to initialize Google Cloud Logging: {e}")
    else:
        # Standard local logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.info("Local logging initialized.")

if __name__ == "__main__":
    setup_cloud_logging()
    logging.info("Test log message")
