import logging
import os

def setup_logging(config):
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        filename=os.path.join(log_dir, config['logging']['log_file_name']),
        level=config['logging']['level'].upper(),
        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s'
    )
    logging.getLogger().addHandler(logging.StreamHandler())