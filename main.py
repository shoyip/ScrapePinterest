import time
import json
import random
import pandas as pd

from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from urllib.parse import quote_plus


def human_sleep(min_seconds: float = 3.0, max_seconds: float = 5.0) -> None:
    """Sleep a random amount of time to simulate human behaviour."""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def safe_get(driver, url: str, max_attempts: int = 3) -> None:
    """
    Load a URL with basic retry logic.
    If the page appears empty for too long, it refreshes.
    """
    attempts = 0
    while attempts < max_attempts:
        driver.get(url)
        human_sleep()
        # Heuristic: if body has some text, assume we are loaded enough
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


def scrape_reddit_search(driver, keyword, subreddit):
    encoded_keyword = quote_plus(keyword)
    search_url = (
        f"https://old.reddit.com/r/{subreddit}/search"
        f"?q={encoded_keyword}&restrict_sr=on&sort=relevance&t=all"
    )

    post_urls = []
    seen_urls = set()

    page_index = 1
    while True:
        print(f"\nLoading Reddit search page {page_index}: {search_url}")
        safe_get(driver, search_url)

        stuck_iterations = 0
        while True:
            posts = driver.find_elements(By.CLASS_NAME, "search-result")
            if not posts:
                stuck_iterations += 1
                if stuck_iterations >= 3:
                    print("No posts found on this page after several tries, refreshing...")
                    try:
                        driver.refresh()
                    except Exception:
                        pass
                    human_sleep()
                    posts = driver.find_elements(By.CLASS_NAME, "search-result")
                    if not posts:
                        print("Still no posts after refresh, moving on.")
                        break
                else:
                    human_sleep()
                    continue

            before_count = len(seen_urls)
            print("The results of the current Reddit search page are:")
            for post in posts:
                try:
                    title_link = post.find_element(By.CLASS_NAME, "search-title")
                    url = title_link.get_attribute("href")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        post_urls.append(url)
                        print(url)
                except Exception:
                    continue

            after_count = len(seen_urls)
            if after_count == before_count:
                # No new posts on this page after scrolling, stop inner loop
                break

            # Scroll down to load more (even though old Reddit uses pagination,
            # this helps mimic natural behaviour)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            human_sleep()

        # Try to go to the next page, if any
        next_link = None
        try:
            # Old Reddit uses "next »" style button
            next_buttons = driver.find_elements(By.CSS_SELECTOR, "span.next-button a")
            if next_buttons:
                next_link = next_buttons[0].get_attribute("href")
        except Exception:
            next_link = None

        if not next_link:
            print("No more Reddit result pages.")
            break

        search_url = next_link
        page_index += 1

    return post_urls


def scrape_reddit_post(driver, post_url, subreddit):
    safe_get(driver, post_url)

    try:
        title_el = driver.find_element(By.CSS_SELECTOR, ".sitetable .thing .entry .title .title")
        title = title_el.text
    except Exception:
        title = None

    try:
        time_el = driver.find_element(By.CSS_SELECTOR, ".entry .tagline time")
        time_ = time_el.get_attribute("datetime")
    except Exception:
        time_ = None

    try:
        author_el = driver.find_element(By.CSS_SELECTOR, ".thing .author")
        author = author_el.text
    except Exception:
        author = None

    try:
        score_el = driver.find_element(By.CSS_SELECTOR, ".score.unvoted")
        score = score_el.text
    except Exception:
        score = None

    try:
        comments_el = driver.find_element(By.CSS_SELECTOR, ".entry .comments")
        comments = int(comments_el.text.split(" ")[0])
    except Exception:
        comments = None

    try:
        text_el = driver.find_element(By.CSS_SELECTOR, "#siteTable .entry .usertext")
        text = text_el.text
    except Exception:
        text = None

    try:
        thumbnails_els = driver.find_elements(By.CSS_SELECTOR, ".entry .preview")
        thumbnails_urls = [el.get_attribute("src") for el in thumbnails_els]
    except Exception:
        thumbnails_urls = None

    entry_dict = {
        "url": post_url,
        "title": title,
        "time": time_,
        "subreddit": subreddit,
        "author": author,
        "score": score,
        "comments": comments,
        "text": text,
        "medias": thumbnails_urls
    }

    print(json.dumps(entry_dict, indent=2, ensure_ascii=False))

    return entry_dict


def scrape_search(driver, keyword="ghibliai"):
    search_url = f"https://fr.pinterest.com/search/pins/?q={keyword}"
    print(f"\nLoading Pinterest search page: {search_url}")
    safe_get(driver, search_url)

    pins_url = []
    seen_urls = set()
    no_new_counter = 0
    max_no_new = 3

    while True:
        try:
            container = driver.find_element(By.CLASS_NAME, "masonryContainer")
            list_ = container.find_element(By.XPATH, "//div[@role='list']")
            list_items = list_.find_elements(By.XPATH, "//div[@role='listitem']")
        except Exception:
            print("Could not find Pinterest results container, refreshing...")
            try:
                driver.refresh()
            except Exception:
                pass
            human_sleep()
            try:
                container = driver.find_element(By.CLASS_NAME, "masonryContainer")
                list_ = container.find_element(By.XPATH, "//div[@role='list']")
                list_items = list_.find_elements(By.XPATH, "//div[@role='listitem']")
            except Exception:
                print("Still unable to locate results container, stopping.")
                break

        before_count = len(seen_urls)
        print("The results of the current Pinterest view are:")
        for list_item in list_items:
            try:
                link = list_item.find_element(By.TAG_NAME, "a")
                link_url = link.get_attribute("href")
                if link_url and link_url not in seen_urls:
                    seen_urls.add(link_url)
                    pins_url.append(link_url)
                    print(link_url)
            except Exception:
                continue

        after_count = len(seen_urls)
        if after_count == before_count:
            no_new_counter += 1
        else:
            no_new_counter = 0

        if no_new_counter >= max_no_new:
            print("No new Pinterest results after several scrolls, stopping.")
            break

        # Scroll down and wait for new content to load
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        human_sleep()

    return pins_url


def scrape_pin(driver, pin_url):
    safe_get(driver, pin_url)

    id_ = None
    created_at = None
    username = None
    followers = None
    description = None
    likes = None
    color = None

    try:
        data_el = driver.find_element(By.XPATH, "//script[@type='application/json']")
        data_text = data_el.get_attribute("innerHTML")
        data = json.loads(data_text)
        pins_data = data.get("initialReduxState", {}).get("pins", {})
        pin_data = next(iter(pins_data.values()), None)
        id_ = next(iter(pins_data.keys()), None)
    except Exception:
        pin_data = None

    if pin_data:
        try:
            print("Pin ID", id_)
        except Exception:
            pass

        try:
            created_at = pin_data.get("created_at")
            print("Date of Creation:", created_at)
        except Exception:
            created_at = None

        try:
            attribution = pin_data.get("closeup_attribution")
            if attribution is not None:
                username = attribution.get("username")
                followers = attribution.get("follower_count")
                print("Username of Creator:", username)
                print("Followers of Creator:", followers)
            else:
                print("No data about Creator.")
        except Exception:
            username = None
            followers = None

        try:
            description = pin_data.get("auto_alt_text")
            print("Auto Description:", description)
        except Exception:
            description = None

        try:
            likes = pin_data.get("share_count")
            print("Number of Likes:", likes)
        except Exception:
            likes = None

        try:
            color = pin_data.get("dominant_color")
            print("Dominant Color:", color)
        except Exception:
            color = None

    entry_dict = {
        "id": id_,
        "created_at": created_at,
        "username": username,
        "followers": followers,
        "description": description,
        "likes": likes,
        "color": color,
    }
    return entry_dict


def create_driver():
    """
    Create a Chrome WebDriver configured for Arch / google-chrome-stable.
    """
    options = Options()

    # If google-chrome-stable is not on the default path for Selenium,
    # explicitly point to it (this is the usual Arch path):
    # options.binary_location = "/usr/bin/google-chrome-stable"

    # If you want to attach to an already running Chrome with remote debugging:
    # 1) Start Chrome manually, e.g.:
    #    google-chrome-stable --remote-debugging-port=9222 --user-data-dir=/home/shoichi/.config/google-chrome-scraper
    # 2) Uncomment the next line so Selenium attaches to that session:
    # options.debugger_address = "localhost:9222"

    # Optional: reuse a specific Chrome profile instead of a fresh one each time:
    # options.add_argument("--user-data-dir=/home/shoichi/.config/google-chrome")
    # options.add_argument("--profile-directory=Default")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


if __name__ == "__main__":
    print("\nSCRAPER")
    print("=======\n")

    driver = create_driver()

    platform = input("Choose platform to scrape (pinterest/reddit): ").strip().lower()
    keyword = input("Enter keyword to search for: ").strip() or "ghibliai"

    if platform == "reddit":
        print(f"\nTarget platform: Reddit\nTarget keyword: {keyword}\n")
        print("Starting to scrape the Reddit results page...\n")
        subreddit = input("Which subreddit? ")
        post_urls = scrape_reddit_search(driver=driver, keyword=keyword, subreddit=subreddit)
        print("\nVisiting each Reddit post and gathering data...\n")
        list_of_entries = []
        for result_idx, post_url in enumerate(post_urls):
            print(f"\nPOST #{result_idx}")
            entry_dict = scrape_reddit_post(driver=driver, post_url=post_url, subreddit=subreddit)
            human_sleep()
            list_of_entries.append(entry_dict)
        if list_of_entries:
            df = pd.DataFrame(list_of_entries)
            df.to_csv("reddit_output.csv", index=False)
            print("Saved Reddit results to reddit_output.csv.")
        else:
            print("No Reddit posts scraped.")
    else:
        print(f"\nTarget platform: Pinterest\nTarget keyword: {keyword}\n")
        print("Starting to scrape the Pinterest results page...\n")
        pins_url = scrape_search(driver=driver, keyword=keyword)

        # Save discovered Pinterest URLs to a file
        urls_path = "pinterest_urls.txt"
        with open(urls_path, "w", encoding="utf-8") as f:
            for url in pins_url:
                f.write(url + "\n")
        print(f"\nSaved {len(pins_url)} Pinterest URLs to {urls_path}.")

        # Close current driver and reopen a new one before visiting each pin
        driver.quit()
        driver = create_driver()

        # Reload URLs from file (source of truth)
        with open(urls_path, "r", encoding="utf-8") as f:
            pins_url = [line.strip() for line in f if line.strip()]

        print("\nVisiting each Pinterest pin and gathering data...\n")
        list_of_entries = []
        for result_idx, pin_url in enumerate(pins_url):
            print(f"\nPOST #{result_idx}")
            entry_dict = scrape_pin(driver=driver, pin_url=pin_url)
            human_sleep()
            list_of_entries.append(entry_dict)
        if list_of_entries:
            df = pd.DataFrame(list_of_entries).set_index("id")
            df.to_csv("output.csv")
            print("Saved Pinterest results to output.csv.")
        else:
            print("No Pinterest pins scraped.")

    driver.quit()
