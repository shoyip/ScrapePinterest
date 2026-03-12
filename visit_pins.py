import json
import random
import time
from pathlib import Path

import pandas as pd
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


def human_sleep(min_seconds: float = 3.0, max_seconds: float = 5.0) -> None:
    """Sleep a random amount of time to simulate human behaviour."""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def create_driver():
    """
    Create a Chrome WebDriver configured for Arch / google-chrome-stable.
    Adjust binary_location or debugger_address here if needed.
    """
    options = Options()

    # If google-chrome-stable is not on the default path for Selenium,
    # explicitly point to it (this is the usual Arch path):
    # options.binary_location = "/usr/bin/google-chrome-stable"

    use_remote_debug = input(
        "Attach to existing Chrome on port 9222? (y/n): "
    ).strip().lower() == "y"

    if use_remote_debug:
        # Attach to an already running Chrome with remote debugging on port 9222
        # Make sure you started Chrome with:
        #   google-chrome-stable --remote-debugging-port=9222 --user-data-dir=/path/to/profile
        options.debugger_address = "localhost:9222"

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def safe_get(driver, url: str, max_attempts: int = 3) -> None:
    """
    Load a URL with basic retry logic.
    If the page appears empty for too long, it refreshes.
    """
    attempts = 0
    while attempts < max_attempts:
        driver.get(url)
        human_sleep()
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if body_text.strip():
                return
        except Exception:
            pass

        attempts += 1
        try:
            driver.refresh()
        except Exception:
            pass
        human_sleep()


def scrape_pin(driver, pin_url: str):
    """
    Visit a single Pinterest pin and extract its data using the original logic.
    """
    max_attempts = 3
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            driver.get(pin_url)
            # Wait until the page reports it is fully loaded, with a small timeout
            for _ in range(10):
                try:
                    state = driver.execute_script("return document.readyState")
                except Exception:
                    state = None
                if state == "complete":
                    break
                time.sleep(0.5)

            # Extra small wait to let dynamic JSON be injected
            time.sleep(1.5)
            data_el = driver.find_element(By.XPATH, "//script[@type='application/json']")
            data_text = data_el.get_attribute("innerHTML")
            data = json.loads(data_text)
            # print(json.dumps(data, indent=2))
            pins_data = data["initialReduxState"]["pins"]
            pin_data = next(iter(pins_data.values()), None)
            id_ = next(iter(pins_data.keys()), None)

            print("Pin ID", id_)
            print("Date of Creation:", pin_data["created_at"])
            created_at = pin_data["created_at"]
            if pin_data["closeup_attribution"] is not None:
                print("Username of Creator:", pin_data["closeup_attribution"]["username"])
                username = pin_data["closeup_attribution"]["username"]
                print("Username of Creator:", pin_data["closeup_attribution"]["follower_count"])
                followers = pin_data["closeup_attribution"]["follower_count"]
            else:
                print("No data about Creator.")
                username = None
                followers = None
            print("Auto Description:", pin_data["auto_alt_text"])
            description = pin_data["auto_alt_text"]
            print("Number of Likes:", pin_data["share_count"])
            likes = pin_data["share_count"]
            print("Dominant Color:", pin_data["dominant_color"])
            color = pin_data["dominant_color"]

            entry_dict = {
                "id": id_,
                "created_at": created_at,
                "username": username,
                "followers": followers,
                "description": description,
                "likes": likes,
                "color": color,
            }
            print(f"Scraped pin {pin_url}:")
            print(json.dumps(entry_dict, indent=2, ensure_ascii=False))
            return entry_dict

        except KeyError as e:
            # Specifically handle missing "initialReduxState"
            last_error = e
            print(
                f"KeyError while parsing Pinterest JSON on attempt {attempt} "
                f"for {pin_url}: {e}. Refreshing and retrying..."
            )
            try:
                driver.refresh()
            except Exception:
                pass
            time.sleep(2)
            continue
        except Exception as e:
            last_error = e
            print(f"Unexpected error while scraping pin {pin_url} on attempt {attempt}: {e}")
            try:
                driver.refresh()
            except Exception:
                pass
            time.sleep(2)
            continue

    # If we get here, all attempts failed – return null values for this URL
    print(f"Failed to scrape pin {pin_url} after {max_attempts} attempts. "
          f"Last error: {last_error}. Returning null values.")
    return {
        "id": None,
        "created_at": None,
        "username": None,
        "followers": None,
        "description": None,
        "likes": None,
        "color": None,
    }


def main():
    urls_path = Path("pinterest_urls.txt")
    if not urls_path.exists():
        print(f"{urls_path} not found. Make sure you ran the discovery script first.")
        return

    with urls_path.open("r", encoding="utf-8") as f:
        pins_url = [line.strip() for line in f if line.strip()]

    if not pins_url:
        print("No URLs found in pinterest_urls.txt.")
        return

    driver = create_driver()

    entries = []
    try:
        for idx, url in enumerate(pins_url):
            print(f"\nVisiting Pinterest pin #{idx}: {url}")
            entry = scrape_pin(driver, url)
            entry["url"] = url
            entries.append(entry)
            human_sleep()
    finally:
        driver.quit()

    if entries:
        df = pd.DataFrame(entries)
        df.set_index("id", inplace=False).to_csv("pinterest_pins_output.csv", index=False)
        print(f"\nSaved {len(entries)} Pinterest pin records to pinterest_pins_output.csv.")
    else:
        print("No pin data scraped.")


if __name__ == "__main__":
    main()

