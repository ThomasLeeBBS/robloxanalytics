import logging
from google.cloud import firestore

class FirestoreHandler:
    def __init__(self, config):
        self.db = None
        self._initialize(config)

    def _initialize(self, config):
        """Initializes the Firestore client."""
        try:
            self.db = firestore.Client(
                project=config['gcp']['project_id'],
                database=config['gcp']['firestore_database_id']
            )
            logging.info("Successfully initialized Firestore client.")
        except Exception as e:
            logging.critical(f"Failed to initialize Firestore client: {e}", exc_info=True)
            raise

    def upsert_game(self, game_data):
        """Upserts basic game info into the 'games' collection."""
        place_id_str = str(game_data['place_id'])
        game_doc_ref = self.db.collection('games').document(place_id_str)
        
        data_to_set = {
            'name': game_data['name'],
            'place_id': game_data['place_id'],
            'universe_id': game_data.get('universe_id'),
            'current_rolimons_player_count': game_data.get('rolimons_player_count'),
            'last_fetched_rolimons_list_data_timestamp': firestore.SERVER_TIMESTAMP
        }
        
        try:
            game_doc_ref.set(data_to_set, merge=True)
            logging.info(f"Upserted game: {game_data['name']} (ID: {place_id_str})")
            return True
        except Exception as e:
            logging.error(f"Error upserting game {game_data['name']}: {e}")
            return False

    def insert_daily_stats(self, place_id_str, daily_stats):
        """Inserts daily stats into a game's subcollection."""
        if not daily_stats:
            logging.info(f"No daily stats to insert for game {place_id_str}.")
            return

        game_doc_ref = self.db.collection('games').document(place_id_str)
        stats_subcollection_ref = game_doc_ref.collection('daily_stats')
        batch = self.db.batch()

        for date_str, stats in daily_stats.items():
            day_doc_ref = stats_subcollection_ref.document(date_str)
            batch.set(day_doc_ref, stats, merge=True)
        
        try:
            batch.commit()
            game_doc_ref.update({'last_scraped_daily_stats_timestamp': firestore.SERVER_TIMESTAMP})
            logging.info(f"Committed {len(daily_stats)} daily stat records for game {place_id_str}.")
        except Exception as e:
            logging.error(f"Error committing daily stats for game {place_id_str}: {e}")