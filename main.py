import time
import json
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def scrape_search(driver, keyword="ghibliai"):
    driver.get(f"https://fr.pinterest.com/search/pins/?q={keyword}")
    time.sleep(5)
    container = driver.find_element(By.CLASS_NAME, "masonryContainer")
    list_ = container.find_element(By.XPATH, "//div[@role='list']")
    list_items = list_.find_elements(By.XPATH, "//div[@role='listitem']")
    pins_url = []
    print("The results of the current search are:")
    for list_item in list_items:
        link = list_item.find_element(By.TAG_NAME, "a")
        link_url= link.get_attribute("href")
        pins_url.append(link_url)
        print(link_url)
    return pins_url


def scrape_pin(driver, pin_url):
    driver.get(pin_url)
    time.sleep(2)
    data_el = driver.find_element(By.XPATH, "//script[@type='application/json']")
    data_text = data_el.get_attribute("innerHTML")
    data = json.loads(data_text)
    #print(json.dumps(data, indent=2))
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
                "color": color
    }
    return entry_dict

if __name__ == "__main__":
    print("\nPINTEREST SCRAPER")
    print("=================\n")
    options = Options()
    options.debugger_address = "localhost:9222"
#    options.add_argument("--user-data-dir=/home/shoichi/.config/google-chrome")
#    options.add_argument("--profile-directory=Default")

    driver = webdriver.Chrome(options=options)
    keyword = "ghibliai"

    print(f"Target keyword for scraping is: {keyword}\n")
    print("Starting to scrape the results page...\n")
    pins_url = scrape_search(driver=driver, keyword="ghibliai")
    print("\nVisiting each page and gathering data...\n")
    list_of_entries = []
    for result_idx, pin_url in enumerate(pins_url):
        print(f"\nPOST #{result_idx}")
        entry_dict = scrape_pin(driver=driver, pin_url=pin_url)
        list_of_entries.append(entry_dict)
    df = pd.DataFrame(list_of_entries).set_index("id")
    df.to_csv("output.csv")
    print("Saved results to output.csv.")

    driver.quit()
