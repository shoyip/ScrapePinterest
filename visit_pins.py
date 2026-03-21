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
            time.sleep(2)
            driver.execute_script("window.scrollBy(0, 547);")
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

    # --- ID helpers ---------------------------------------------------------
    def normalize_id(value):
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        try:
            return str(int(s))
        except Exception:
            return s

    def id_from_url(url: str):
        if not url:
            return None
        raw = str(url).split("?", 1)[0].split("#", 1)[0]
        parts = [p for p in raw.split("/") if p]
        if len(parts) < 2:
            return None
        cand = parts[-1] if parts[-1].isdigit() else parts[-2]
        return normalize_id(cand)

    # Load existing results if any, clean them up, and build a visited ID set.
    results_path = Path("pinterest_pins_output.csv")
    existing_df = None
    visited_ids = set()
    if results_path.exists():
        try:
            existing_df = pd.read_csv(results_path)

            wanted_cols = ["id", "created_at", "username", "followers", "description", "likes", "color", "url"]
            existing_df = existing_df[[c for c in existing_df.columns if c in wanted_cols]]

            if "url" in existing_df.columns:
                existing_df["url"] = existing_df["url"].astype(str)

            if "id" not in existing_df.columns:
                existing_df["id"] = None

            def fill_id(row):
                cur_id = row.get("id")
                if pd.isna(cur_id) or cur_id is None or str(cur_id).strip() == "":
                    return id_from_url(row.get("url"))
                return normalize_id(cur_id)

            existing_df["id"] = existing_df.apply(fill_id, axis=1)
            existing_df["id_norm"] = existing_df["id"].apply(normalize_id)
            existing_df = existing_df[existing_df["id_norm"].notna()]
            existing_df = existing_df.drop_duplicates(subset=["id_norm"], keep="last")

            visited_ids = set(existing_df["id_norm"].tolist())
            print(f"Loaded {len(visited_ids)} existing unique pin IDs from {results_path}.")
        except Exception as e:
            print(f"Could not read existing results from {results_path}: {e}")

    driver = create_driver()

    # We will accumulate new/updated entries in this list
    new_entries = []

    try:
        for idx, url in enumerate(pins_url):
            url = str(url)
            pin_id = id_from_url(url)

            already_visited = pin_id is not None and pin_id in visited_ids
            print(f"\n[DEBUG] index={idx}, url={url}, id={pin_id}, id_in_csv={already_visited}")

            if already_visited:
                print("Action: SKIP (ID already scraped)")
                continue

            print("Action: VISIT (new or ID-less pin)")

            try:
                entry = scrape_pin(driver, url)
                entry["url"] = url
                scraped_id = normalize_id(entry.get("id")) or pin_id
                entry["id"] = scraped_id
                if scraped_id is not None:
                    visited_ids.add(scraped_id)
                new_entries.append(entry)
                human_sleep()
            except KeyboardInterrupt:
                print("\nStopping pin visit due to keyboard interrupt.")
                break
    finally:
        driver.quit()

    if new_entries or existing_df is not None:
        # Combine existing rows (if any) with new ones, then deduplicate by normalized ID.
        if existing_df is not None:
            existing_df = existing_df.drop(columns=[c for c in existing_df.columns if c == "id_norm"], errors="ignore")
            combined_df = pd.concat(
                [existing_df, pd.DataFrame(new_entries)],
                ignore_index=True
            )
        else:
            combined_df = pd.DataFrame(new_entries)

        if "id" in combined_df.columns:
            combined_df["id_norm"] = combined_df["id"].apply(normalize_id)
            combined_df = combined_df[combined_df["id_norm"].notna()]
            combined_df = combined_df.drop_duplicates(subset=["id_norm"], keep="last")
            combined_df = combined_df.drop(columns=["id_norm"])

        combined_df.set_index("id", inplace=False).to_csv(results_path, index=False)
        print(f"\nSaved {len(combined_df)} Pinterest pin records to {results_path}.")
    else:
        print("No pin data scraped.")


if __name__ == "__main__":
    main()

