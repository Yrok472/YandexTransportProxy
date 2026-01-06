"""
Yandex Transport Core module

This is the core module of Yandex Transport Hack API.
It uses Selenium with ChromeDriver and gets Yandex Transport API JSON responses.
"""

# NOTE: This project uses camelCase for function names. While PEP8 recommends using snake_case for these,
#       the project in fact implements the "quasi-API" for Yandex Masstransit, where names are in camelCase,
#       for example, get_stop_info. Correct naming for this function according to PEP8 would be get_stop_info.
#       Thus, the decision to use camelCase was made. In fact, there are a bunch of python projects which use
#       camelCase, like Robot Operating System.
#       I also personally find camelCase more prettier than the snake_case.

import ast
import re
import time
import io
import json
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from .logger import Logger

class YandexTransportCore:
    """
    YandexTransportCore class, implements core functions of access to Yandex Transport/Masstransit API
    """
    # Error codes
    RESULT_OK = 0
    RESULT_WEBDRIVER_NOT_RUNNING = 1
    RESULT_NO_LAST_QUERY = 2
    RESULT_NETWORK_PARSE_ERROR = 3
    RESULT_JSON_PARSE_ERROR = 4
    RESULT_GET_ERROR = 5

    def __init__(self, log_level=None):
        self.driver = None
        self.log = Logger(log_level) if log_level is not None else None

        # Count of network queries executed so far, the idea is to restart the browser if it's too big.
        self.network_queries_count = 0

        # ChromeDriver location. They changed it a lot, by the way.
        self.chrome_driver_location = "/usr/bin/chromedriver"
        
        # Cache currently loaded URL to optimize repeated queries
        self.current_url = None
        
        # Multi-tab support for preload cache
        self.tabs = {}  # {url: window_handle}
        self.main_tab = None

    def start_webdriver(self):
        """
        Start Chromium webdriver
        :return: nothing
        """
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--incognito")
        # These two are basically needed for Chromium to run inside docker container.
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Memory optimization options
        chrome_options.add_argument('--disable-gpu')  # Disable GPU acceleration in headless mode
        chrome_options.add_argument('--disable-software-rasterizer')  # Reduce memory usage
        chrome_options.add_argument('--disable-extensions')  # No extensions
        chrome_options.add_argument('--disable-background-networking')  # Reduce background activity
        chrome_options.add_argument('--disable-background-timer-throttling')  # Better performance
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')  # Reduce memory for hidden tabs
        chrome_options.add_argument('--disable-breakpad')  # Disable crash reporting
        chrome_options.add_argument('--disable-component-extensions-with-background-pages')
        chrome_options.add_argument('--disable-features=TranslateUI')  # Disable translation
        chrome_options.add_argument('--disable-ipc-flooding-protection')  # Better performance in automation
        chrome_options.add_argument('--disable-renderer-backgrounding')  # Keep renderer active
        chrome_options.add_argument('--metrics-recording-only')  # Minimal metrics
        chrome_options.add_argument('--mute-audio')  # No audio processing
        chrome_options.add_argument('--no-first-run')  # Skip first run wizards
        chrome_options.add_argument('--no-default-browser-check')  # Skip browser checks
        chrome_options.add_argument('--autoplay-policy=user-gesture-required')  # No autoplay
        chrome_options.add_argument('--disable-hang-monitor')  # Disable hang monitoring
        chrome_options.add_argument('--disable-prompt-on-repost')  # No repost prompts
        chrome_options.add_argument('--disable-sync')  # No sync
        chrome_options.add_argument('--force-color-profile=srgb')  # Standard colors
        chrome_options.add_argument('--password-store=basic')  # Basic password store
        
        # Enable performance logging for network requests
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        # Use webdriver-manager to automatically download and manage chromedriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Store main tab handle
        self.main_tab = self.driver.current_window_handle

    def stop_webdriver(self):
        """
        Stop Chromium Webdriver
        :return: nothing
        """
        self.driver.quit()

    def restart_webdriver(self):
        """
        Restart Chromium Webdriver. Good idea to do this sometimes, like Garbage Collection.
        :return: nothing
        """
        self.stop_webdriver()
        self.start_webdriver()

    @staticmethod
    def yandex_api_to_local_api(method):
        """
        Converts Yandex API to local API,
        :param method: method, like "maps/api/masstransit/getVehciclesInfo"
        :return: local API, like to "getVehiclesInfo"
        """
        if method == "maps/api/masstransit/getStopInfo":
            return 'getStopInfo'
        if method == "maps/api/masstransit/getRouteInfo":
            return 'getRouteInfo'
        if method == "maps/api/masstransit/getLine":
            return 'getLine'
        if method == "maps/api/masstransit/getVehiclesInfo":
            return 'getVehiclesInfo'
        if method == "maps/api/masstransit/getVehiclesInfoWithRegion":
            return 'getVehiclesInfoWithRegion'
        if method == "maps/api/masstransit/getLayerRegions":
            return 'getLayerRegions'

        return method

    def create_tab_for_url(self, url):
        """
        Create a new tab for the given URL (for preload cache)
        :param url: URL to load in new tab
        :return: window handle of new tab
        """
        if self.driver is None:
            return None
        
        # Open new tab
        self.driver.execute_script("window.open('');")
        # Switch to new tab
        new_tab = self.driver.window_handles[-1]
        self.driver.switch_to.window(new_tab)
        
        # Store tab handle
        self.tabs[url] = new_tab
        
        if self.log:
            self.log.debug(f"Created tab for URL: {url}")
        
        return new_tab
    
    def switch_to_tab(self, url):
        """
        Switch to existing tab for URL
        :param url: URL whose tab to switch to
        :return: True if switched, False if tab not found
        """
        if url not in self.tabs:
            return False
        
        try:
            self.driver.switch_to.window(self.tabs[url])
            return True
        except Exception as e:
            if self.log:
                self.log.warning(f"Failed to switch to tab for {url}: {e}")
            # Remove stale tab handle
            del self.tabs[url]
            return False
    
    def switch_to_main_tab(self):
        """
        Switch back to main tab
        """
        if self.main_tab:
            try:
                self.driver.switch_to.window(self.main_tab)
            except Exception as e:
                if self.log:
                    self.log.warning(f"Failed to switch to main tab: {e}")

    def get_chromium_networking_data(self):
        """
        Gets "Network" data from Chrome Performance logs
        :return: List containing network requests data
        """
        try:
            # Get performance logs from Chrome
            logs = self.driver.get_log('performance')
            
            network_data = []
            for log_entry in logs:
                try:
                    log_message = json.loads(log_entry['message'])
                    message = log_message.get('message', {})
                    method = message.get('method', '')
                    
                    # Filter only network requests
                    if 'Network.requestWillBeSent' in method:
                        params = message.get('params', {})
                        request = params.get('request', {})
                        url = request.get('url', '')
                        
                        if url:
                            network_data.append({
                                'name': url,
                                'entryType': 'resource'
                            })
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    # Skip malformed log entries
                    continue
            
            if self.log:
                self.log.debug(f"Found {len(network_data)} network entries")
            
            return network_data if network_data else []
        except Exception as e:
            if self.log:
                self.log.error(f"Failed to get network data: {e}")
            return []

    # ----                               MASTER FUNCTION TO GET YANDEX API DATA                                   ---- #

    def _get_yandex_json(self, url, api_method):
        """
        Universal method to get Yandex JSON results.
        :param url: initial url, get it by clicking on the route or stop
        :param api_method: tuple of strings to find,
               like ("maps/api/masstransit/get_route_info","maps/api/masstransit/get_vehicles_info")
        :return: array of huge json data, error code
        """

        if self.log:
            self.log.debug(f"API Method: {api_method}")
            self.log.debug(f"URL: {url}")

        result_list = []

        if self.driver is None:
            return result_list, self.RESULT_WEBDRIVER_NOT_RUNNING
        
        # Check if we're requesting the same URL as before (optimization)
        same_url = (self.current_url == url)
        
        if same_url:
            if self.log:
                self.log.info(f"URL already loaded, refreshing page for fresh data...")
            # Clear old logs before refresh
            try:
                self.driver.get_log('performance')
                if self.log:
                    self.log.debug("Cleared old performance logs before refresh")
            except Exception as e:
                if self.log:
                    self.log.warning(f"Failed to clear performance logs: {e}")
            # Refresh page to get fresh data (faster than full reload)
            try:
                self.driver.refresh()
            except selenium.common.exceptions.WebDriverException as e:
                if self.log:
                    self.log.error(f"Selenium exception (refresh): {e}")
                return None, self.RESULT_GET_ERROR
        else:
            if self.log:
                self.log.info(f"Loading new URL: {url}")
            # Clear old performance logs before loading new URL to avoid mixing old and new data
            try:
                self.driver.get_log('performance')  # Read and discard old logs
                if self.log:
                    self.log.debug("Cleared old performance logs before loading new URL")
            except Exception as e:
                if self.log:
                    self.log.warning(f"Failed to clear performance logs: {e}")
            
            try:
                self.driver.get(url)
                self.current_url = url  # Update cached URL
            except selenium.common.exceptions.WebDriverException as e:
                if self.log:
                    self.log.error(f"Selenium exception (_get_yandex_json): {e}")
                return None, self.RESULT_GET_ERROR

        # Wait for specific API methods to appear in performance logs (with timeout)
        # Accumulate all logs during polling since get_log() clears them
        if self.log:
            self.log.info(f"Waiting for API methods {api_method} to appear in network logs...")
        
        max_wait = 45
        check_interval = 1
        waited = 0
        api_found = False
        accumulated_logs = []
        
        while waited < max_wait:
            time.sleep(check_interval)
            waited += check_interval
            
            # Check if any of the target API methods appeared in performance logs
            try:
                logs = self.driver.get_log('performance')
                accumulated_logs.extend(logs)  # Accumulate logs since get_log() clears them
                
                for log_entry in logs:
                    try:
                        log_message = json.loads(log_entry['message'])
                        message = log_message.get('message', {})
                        if 'Network.requestWillBeSent' in message.get('method', ''):
                            url = message.get('params', {}).get('request', {}).get('url', '')
                            # Check if any of the target API methods is in this URL
                            for method in api_method:
                                if method in url:
                                    api_found = True
                                    if self.log:
                                        self.log.info(f"Found {method} after {waited} seconds")
                                    break
                            if api_found:
                                break
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
                
                if api_found:
                    break
            except Exception as e:
                if self.log:
                    self.log.warning(f"Error checking performance logs: {e}")
        
        if not api_found and self.log:
            self.log.warning(f"API methods {api_method} not found after {waited} seconds, proceeding anyway")

        # Parse accumulated logs to extract network data
        network_data = []
        for log_entry in accumulated_logs:
            try:
                log_message = json.loads(log_entry['message'])
                message = log_message.get('message', {})
                if 'Network.requestWillBeSent' in message.get('method', ''):
                    url = message.get('params', {}).get('request', {}).get('url', '')
                    if url:
                        network_data.append({'name': url, 'entryType': 'resource'})
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        if self.log:
            self.log.debug(f"Found {len(network_data)} network entries from accumulated logs")
        if self.log:
            self.log.debug(f"Network data: {network_data}")

        # Loading Network Data to JSON
        #try:
        #    network_data = json.loads(network_json, encoding='utf-8')
        #except ValueError as e:
        #    print("JSON Exception (_get_yandex_json):", e)
        #    return result_list, self.RESULT_NETWORK_PARSE_ERROR

        url_reached = False
        last_query = []

        self.network_queries_count = 0
        
        # DEBUG: Log all masstransit API calls
        if self.log:
            masstransit_urls = [entry['name'] for entry in network_data if 'masstransit' in entry['name'].lower()]
            if masstransit_urls:
                self.log.debug(f"Found {len(masstransit_urls)} masstransit API calls:")
                for mt_url in masstransit_urls:
                    self.log.debug(f"  - {mt_url}")
        
        for entry in network_data:
            self.network_queries_count += 1
            # Check if this entry matches any of the target API methods
            for method in api_method:
                res = re.match(".*" + method + ".*", str(entry['name']))
                if res is not None:
                    last_query.append({"url": entry['name'], "method": method})
                    break  # Found match, no need to check other methods for this entry

        # Getting last API query results from cache by executing it again in the browser
        if last_query:                    # Same meaning as in "if len(last_query) > 0:"
            for query in last_query:
                # Getting the webpage based on URL
                try:
                    self.driver.get(query['url'])
                except selenium.common.exceptions.WebDriverException as e:
                    if self.log:
                        self.log.error("Your favourite error message: THIS SHOULD NOT HAPPEN!")
                        self.log.error(f"Selenium exception (_get_yandex_json): {e}")
                    return None, self.RESULT_GET_ERROR

                # Writing get_stop_info results to memory
                output_stream = io.StringIO()
                output_stream.write(self.driver.page_source)
                output_stream.seek(0)

                # Getting get_stop_info results to JSON
                soup = BeautifulSoup(output_stream, 'lxml', from_encoding='utf-8')
                body = soup.find('body')
                if body is not None:
                    # Use get_text() instead of .string as .string can be None for complex body
                    body_text = body.get_text() if body.string is None else body.string
                    if body_text:
                        body_string = body_text.encode('utf-8')
                        try:
                            returned_json = json.loads(body_string)
                            data = {"url": query['url'],
                                    "method": self.yandex_api_to_local_api(query['method']),
                                    "error": "OK",
                                    "data": returned_json}
                        except ValueError as e:
                            data = {"url": query['url'],
                                    "method": self.yandex_api_to_local_api(query['method']),
                                    "error": "Failed to parse JSON"}
                    else:
                        data = {"url": query['url'],
                                "method": self.yandex_api_to_local_api(query['method']),
                                "error": "Empty body content"}
                else:
                    data = {"url": query['url'],
                            "method": self.yandex_api_to_local_api(query['method']),
                            "error": "Failed to parse body of the response"}

                result_list.append(data)

        else:
            return result_list, self.RESULT_NO_LAST_QUERY

        return result_list, self.RESULT_OK

    # ----                                   SHORTCUTS TO USED APIs                                               ---- #

    def get_stop_info(self, url):
        """
        Getting Yandex masstransit get_stop_info JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        
        Note: As of 2026, getStopInfo still exists but loads later (needs 5-10s wait)
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getStopInfo",))

    def get_vehicles_info(self, url):
        """
        Getting Yandex masstransit get_vehicles_info JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getVehiclesInfo",))

    def get_vehicles_info_with_region(self, url):
        """
        Getting Yandex masstransit get_vehicles_info JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getVehiclesInfoWithRegion",))

    def get_route_info(self, url):
        """
        Getting Yandex masstransit get_route_info JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getRouteInfo",))

    def get_line(self, url):
        """
        Getting Yandex masstransit get_line JSON results
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getLine",))

    def get_layer_regions(self, url):
        """
        No idea what this thing does
        :param url: url of the stop (the URL you get when you click on the stop in the browser)
        :return: array of huge json data, error code
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getLayerRegions",))

    def get_all_info(self, url):
        """
        Getting basically all Yandex Masstransit API JSON results related to requested URL
        :param url:
        :return:
        """
        return self._get_yandex_json(url, api_method=("maps/api/masstransit/getRouteInfo",
                                                      "maps/api/masstransit/getLine",
                                                      "maps/api/masstransit/getStopInfo",
                                                      "maps/api/masstransit/getVehiclesInfo",
                                                      "maps/api/masstransit/getVehiclesInfoWithRegion",
                                                      "maps/api/masstransit/getLayerRegions")
                                     )


if __name__ == '__main__':
    print("Hi! This module is not supposed to run on its own.")
