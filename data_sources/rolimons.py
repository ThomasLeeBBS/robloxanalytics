import requests
import logging
from operator import itemgetter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import datetime

class RolimonsSource:
    def __init__(self, config):
        self.config = config
        self.chart_map = config['chart_title_map']

    def get_top_games(self):
        """Fetches and sorts the top games from the Rolimons API."""
        try:
            url = self.config['source']['rolimons_api_url']
            limit = self.config['source']['limit']
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            all_games = [
                {"place_id": int(pid), "name": g[0], "rolimons_player_count": int(g[1])}
                for pid, g in data.get("games", {}).items()
            ]
            
            sorted_games = sorted(all_games, key=itemgetter('rolimons_player_count'), reverse=True)
            return sorted_games[:limit]
        except Exception as e:
            logging.critical(f"Failed to get top games from Rolimons API: {e}")
            return []

    def enrich_game_data(self, game_summary):
        """Adds the universe ID to the game summary."""
        place_id = game_summary['place_id']
        url = self.config['source']['roblox_universe_api_url_template'].format(place_id=place_id)
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            game_summary['universe_id'] = int(response.json().get("universeId"))
        except Exception as e:
            logging.warning(f"Could not get universe_id for place_id {place_id}: {e}")
            game_summary['universe_id'] = None
        return game_summary

    def get_daily_stats(self, place_id):
        """Scrapes and processes daily stats for a single game."""
        raw_charts = self._acquire_raw_data(place_id)
        if not raw_charts:
            return {}
        return self._convert_and_group_stats(raw_charts, str(place_id))

    def _acquire_raw_data(self, place_id):
        """The core Selenium logic to get chart data."""
        options = Options()
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        if self.config['selenium']['headless']:
            options.add_argument("--headless")
        
        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.get(f"https://www.rolimons.com/game/{place_id}")
            # Wait for the "Daily" view tab button to be clickable
            daily_tab_selector = '#daily_view_button a'
            WebDriverWait(driver, self.config['selenium']['initial_load_timeout']).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, daily_tab_selector))
            )
            logging.info("Daily view button found. Clicking...")

            # Step 1: Click the "Daily" view tab
            driver.execute_script(f"""
                const dailyTab = document.querySelector('{daily_tab_selector}');
                if (dailyTab) dailyTab.click();
            """)
            # A small static delay here is often okay after a click,
            # but the JS below is the primary wait for data.
            time.sleep(self.config['selenium']['tab_click_delay'])

            # Step 2: Extract all daily Highcharts charts and their series data
            # The JavaScript function checkChartsWithData includes its own retry mechanism
            raw_charts = driver.execute_async_script("""
                const callback = arguments[0];
                function checkChartsWithData(retries = 10) {
                    const charts = Highcharts.charts
                        .filter(c => c && c.renderTo && c.renderTo.id.includes('daily'));
                    const titles = Array.from(document.querySelectorAll('.highcharts-title')).map(t => t.textContent.trim());
                    const allReady = charts.every(c => c.series.length > 0 && c.series[0].data.length > 0);

                    if (allReady || retries <= 0) {
                        const result = charts.map((c, i) => ({
                            title: titles[i] || "Untitled Chart",
                            data: c.series[0].data.map(p => ({x: p.x, y: p.y}))
                        }));
                        callback(result);
                    } else {
                        setTimeout(() => checkChartsWithData(retries - 1), 1000);
                    }
                }
                checkChartsWithData();
            """)
            logging.info(f"Successfully extracted {len(raw_charts)} charts for Place ID: {place_id}")
            return raw_charts
        except Exception as e:
            logging.error(f"Error during data acquisition for Place ID {place_id}: {e}", exc_info=True)
            return []
        finally:
            if driver:
                driver.quit()

    def _convert_and_group_stats(self, raw_charts, game_place_id_str):
        """The logic from your convert_and_group_daily_stats function."""
        daily_grouped_stats = {}
        for chart in raw_charts:
            field_name = self.chart_map.get(chart["title"])
            if not field_name:
                continue
            for point in chart["data"]:
                if point and 'x' in point:
                    date_str_id = datetime.datetime.utcfromtimestamp(point["x"] / 1000).strftime("%Y-%m-%d")
                    if date_str_id not in daily_grouped_stats:
                        daily_grouped_stats[date_str_id] = {}
                    daily_grouped_stats[date_str_id][field_name] = point["y"]
        return daily_grouped_stats