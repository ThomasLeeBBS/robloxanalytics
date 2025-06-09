Recovery code for sendgrid: GB2S941RNZRX7KAJ79336MKY

Type: Host:                             Value: 
CNAME em1715.baobabstudios.com          u53432840.wl091.sendgrid.net
CNAME s1._domainkey.baobabstudios.com   s1.domainkey.u53432840.wl091.sendgrid.net
CNAME s2._domainkey.baobabstudios.com   s2.domainkey.u53432840.wl091.sendgrid.net
TXT   _dmarc.baobabstudios.com            v=DMARC1; p=none;

**Architecture Overview**
This project is built on a serverless, event-driven architecture on Google Cloud Platform (GCP) to maximize cost-efficiency. The primary compute instance is shut down for over 23 hours a day.

The workflow is as follows:

Cloud Scheduler: A cron job triggers once daily (e.g., at 11 PM).
Pub/Sub: The scheduler sends a message to a Pub/Sub topic.
Cloud Function: A lightweight function is subscribed to the topic. On receiving a message, it programmatically starts the Compute Engine VM.
Compute Engine (VM): The VM boots up and runs the main Python scraper script (main.py).
Firestore: The script scrapes data and writes it to the baobab-roblox-statistics-db Firestore database.
Self-Termination: Upon completion, the script calls the GCP API to shut down its own VM instance, stopping all costs.

**Key Features**
Automated Daily Execution: Runs on a schedule without manual intervention.
Cost-Efficient: The Compute Engine instance only runs for the duration of the scrape.
Scalable Data Structure: Firestore provides a flexible NoSQL database that can easily scale.
Modular Codebase: The project is broken into logical components (data_sources, databases, utils) to make it easy to maintain and extend (e.g., adding other API's).

**Project Structure**
rolimons_scraper/
├── main.py                 # Main entry point and orchestrator
├── config.yaml             # Local configuration (Not checked into Git)
├── config.yaml.template    # A template for creating the config file
├── requirements.txt        # Python project dependencies
├── README.md               # This documentation file
├── data_sources/
│   ├── __init__.py         # Exposes data source classes
│   └── rolimons_source.py  # Logic for fetching data from Rolimon's/Roblox APIs
├── databases/
│   ├── __init__.py         # Exposes database handler classes
│   └── firestore_handler.py  # All Firestore-specific logic
└── utils/
    ├── __init__.py         # Exposes utility functions
    ├── gcp.py                # GCP-specific utilities (like VM shutdown)
    └── logging_setup.py      # Centralized logging configuration

**Setup and Installation (Local Environment)**
Follow these steps to run the scraper on your local machine for testing and development.

Prerequisites
    - Python 3.8+
    - A Google Cloud Platform account with an active project.
    - Google Cloud SDK (gcloud CLI) installed.
    - Google Chrome browser installed.

1. Clone the Repository

git clone <your-repository-url>
cd rolimons_scraper

2. Set Up a Virtual Environment 

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

3. Install Dependencies

pip install -r requirements.txt

4. Authenticate with GCP
This command allows your local machine to securely access your GCP resources.

gcloud auth application-default login

5. Configure the Project
Create your own configuration file by copying the template.

cp config.yaml.template config.yaml
Now, edit config.yaml and fill in your specific project details.

6. Set Up Selenium WebDriver
The script uses Selenium to control a Chrome browser.

Check your installed Chrome browser version.
Download the matching version of chromedriver from the Chrome for Testing dashboard.
Place the chromedriver executable in the root of the project directory (next to main.py).

**Usage**
To run the scraper manually from your local machine, execute the main.py script from the root directory.

python main.py
Logs will be printed to the console and also saved to a logs/ directory.

**Module Breakdown**
main.py
This is the main orchestrator. It is responsible for:
    - Loading the configuration from config.yaml.
    - Setting up logging.
    - Initializing the data source and database handler.
    - Executing the main loop: get top games, enrich data, get daily stats, and save to the database.
    - Calling the utility to shut down the VM when running in the cloud.

config.yaml.template
    - A template file showing the required structure for the main configuration. Users must create a config.yaml from this template. This prevents sensitive information from being committed to version control.

data_sources/rolimons_source.py
    - Class RolimonsSource: Contains all logic for acquiring data from external Rolimon's and Roblox sources.
        - get_top_games(): Hits the Rolimon's API to get the list of top games.
        - enrich_game_data(): Gets the universe_id for a game from the Roblox API.
        - get_daily_stats(): The core web scraping method that uses Selenium to launch a browser, navigate to a game's page, and extract the daily chart data.
databases/firestore_handler.py
    - Class FirestoreHandler: Manages all communication with the Google Firestore database.
        - _initialize(): Connects to the specific Firestore database using the project credentials.
        - upsert_game(): Creates or updates a game's main document in the games collection.
        - insert_daily_stats(): Writes the daily statistics for a game into the daily_stats subcollection using an efficient batch write.
utils/
    - This package contains helper modules that are not specific to the core business logic.
        - logging_setup.py: A simple function setup_logging() to configure file and console logging in one place.
        - gcp.py: Contains the shutdown_instance() function, which uses the GCP metadata server to find its own VM name and zone, then issues a gcloud command to stop itself.