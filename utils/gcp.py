import logging
import requests
import subprocess

def shutdown_instance():
    """Shuts down the GCE instance."""
    try:
        metadata_server = "http://metadata.google.internal/computeMetadata/v1/"
        headers = {"Metadata-Flavor": "Google"}
        instance_name = requests.get(f"{metadata_server}instance/name", headers=headers).text
        zone = requests.get(f"{metadata_server}instance/zone", headers=headers).text.split('/')[-1]

        logging.info(f"Attempting to self-shutdown instance '{instance_name}'.")
        subprocess.run(["gcloud", "compute", "instances", "stop", instance_name, "--zone", zone], check=True)
    except Exception as e:
        logging.error(f"Failed to self-shutdown VM: {e}")