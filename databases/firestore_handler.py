import logging
from google.cloud import firestore

class FirestoreHandler:
    def __init__(self, config):
        self.db = None
        self._initialize(config)

    def _initialize(self, config):
        try:
            self.db = firestore.Client(
                project=config['gcp']['project_id'],
                database=config['gcp']['firestore_database_id']
            )
            logging.info("Successfully initialized Firestore client.")
        except Exception as e:
            logging.critical(f"Failed to initialize Firestore client: {e}", exc_info=True)
            raise

    def get_latest_stat_date(self, place_id_str):
        """
        Finds the most recent date string (YYYY-MM-DD) for a game's daily stats.
        This will tell us if a game is new or existing.
        This version does NOT require a special index.
        """
        try:
            stats_subcollection_ref = self.db.collection('games').document(place_id_str).collection('daily_stats')
            docs = stats_subcollection_ref.stream()
            doc_ids = [doc.id for doc in docs]
            return max(doc_ids) if doc_ids else None
        except Exception as e:
            logging.error(f"Error getting latest stat date for {place_id_str}: {e}")
            return None

    def upsert_game(self, game_data):
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

    def write_daily_stats(self, place_id_str, daily_stats):
        """
        Writes a batch of daily stats. The filtering logic is handled before calling this.
        """
        if not daily_stats:
            logging.info(f"No new daily stats to write for game {place_id_str}.")
            return

        game_doc_ref = self.db.collection('games').document(place_id_str)
        
        try:
            @firestore.transactional
            def update_in_transaction(transaction, stats_data):
                stats_subcollection_ref = game_doc_ref.collection('daily_stats')
                for date_str, stats in stats_data.items():
                    day_doc_ref = stats_subcollection_ref.document(date_str)
                    transaction.set(day_doc_ref, stats, merge=True)
                
                transaction.update(game_doc_ref, {
                    'last_scraped_daily_stats_timestamp': firestore.SERVER_TIMESTAMP
                })

            update_in_transaction(self.db.transaction(), daily_stats)
            logging.info(f"Committed {len(daily_stats)} daily stat record(s) for game {place_id_str}.")
        except Exception as e:
            logging.error(f"Error committing daily stats for game {place_id_str}: {e}")