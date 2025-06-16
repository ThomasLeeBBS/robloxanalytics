import yaml
import logging
import time
from datetime import datetime, timedelta, timezone
from utils import setup_logging, shutdown_instance
from data_sources import RolimonsSource
from databases import FirestoreHandler

def main():
    # 1. Load Configuration & Setup
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    setup_logging(config)
    
    try:
        # 2. Initialize Components
        source = RolimonsSource(config)
        db_handler = FirestoreHandler(config)

        # 3. Run the Process
        logging.info(f"Starting daily collection for top {config['source']['limit']} games.")
        top_games = source.get_top_games()

        if not top_games:
            logging.warning("No top games found. Exiting process.")
            return

        # Calculate the 14-day cutoff date string
        utc_now = datetime.now(timezone.utc)
        cutoff_date = utc_now - timedelta(days=14)
        fourteen_day_cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        for i, game_summary in enumerate(top_games):
            place_id_str = str(game_summary['place_id'])
            logging.info(f"Processing game ({i+1}/{len(top_games)}): {game_summary['name']}")
            
            # Upsert the main game document info
            enriched_game = source.enrich_game_data(game_summary)
            db_handler.upsert_game(enriched_game)
            
            # Scrape all available history from the website
            all_scraped_stats = source.get_daily_stats(enriched_game['place_id'])
            if not all_scraped_stats:
                logging.warning(f"Could not acquire any daily stats for {place_id_str}.")
                continue

            # Check if the game is new or existing
            latest_date_in_db = db_handler.get_latest_stat_date(place_id_str)
            
            stats_to_write = {}
            if latest_date_in_db:
                # --- THIS IS THE NEW, UNIFIED LOGIC FOR EXISTING GAMES ---
                # Determine the effective start date for our writes.
                # It's the more recent of our last data point or the 14-day cutoff.
                start_date = max(latest_date_in_db, fourteen_day_cutoff_str)
                logging.info(f"Existing game found. Writing data newer than {start_date}.")
                
                # Filter for stats that are strictly newer than our calculated start_date
                stats_to_write = {
                    date: stats for date, stats in all_scraped_stats.items()
                    if date > start_date
                }
            else:
                # This is a new game, so perform a full backfill
                logging.info("New game found. Performing full backfill of historical data.")
                stats_to_write = all_scraped_stats
            
            # Write the final, intelligently filtered data to the database
            db_handler.write_daily_stats(place_id_str, stats_to_write)

            time.sleep(config['source']['delay_between_games'])

        logging.info("Acquired data successfully.")

    except Exception as e:
        logging.critical(f"A critical error occurred in the main process: {e}", exc_info=True)
    
    finally:
        # 4. Shutdown the VM
        shutdown_instance()

if __name__ == "__main__":
    main()