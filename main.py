import yaml
import logging
import time
from utils import setup_logging, shutdown_instance
from data_sources import RolimonsSource
from databases import FirestoreHandler

def main():
    # 1. Load Configuration
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # 2. Setup Logging
    setup_logging(config)
    
    try:
        # 3. Initialize Components
        source = RolimonsSource(config)
        db_handler = FirestoreHandler(config)

        # 4. Run the Process
        logging.info(f"Starting daily collection for top {config['source']['limit']} games.")
        top_games = source.get_top_games()

        if not top_games:
            logging.warning("No top games found. Exiting process.")
            return

        for i, game_summary in enumerate(top_games):
            logging.info(f"Processing game ({i+1}/{len(top_games)}): {game_summary['name']}")
            
            # Enrich with Universe ID
            enriched_game = source.enrich_game_data(game_summary)
            
            # Save game info to DB
            if not db_handler.upsert_game(enriched_game):
                continue # Skip if game upsert fails
            
            # Acquire and save daily stats
            daily_stats = source.get_daily_stats(enriched_game['place_id'])
            db_handler.insert_daily_stats(str(enriched_game['place_id']), daily_stats)

            time.sleep(config['source']['delay_between_games'])

        logging.info("Acquired data successfully.")

    except Exception as e:
        logging.critical(f"A critical error occurred in the main process: {e}", exc_info=True)
    
    finally:
        # 5. Shutdown the VM
        shutdown_instance()

if __name__ == "__main__":
    main()