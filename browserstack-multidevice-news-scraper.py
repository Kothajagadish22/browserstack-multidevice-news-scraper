import os
import re
import time
import requests
from urllib.parse import urljoin
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver

# ======== Credentials ========
USERNAME = 'kothajagadish_f4v1eG'
ACCESS_KEY = 'sQEf4Pwjup6yak5RZqhR'
RAPIDAPI_KEY = "bd3424cba3mshefc0a0845f0a311p12daf3jsn8571d6eaba5e"
RAPIDAPI_HOST = "rapid-translate-multi-traduction.p.rapidapi.com"


# ======== Utilities ========
def translate_text(text, target_lang='en'):
    if not text.strip():
        return text

    url = "https://rapid-translate-multi-traduction.p.rapidapi.com/t"
    payload = {"from": "auto", "to": target_lang, "q": text}
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()[0][0]
    except Exception as e:
        print(f"Translation error: {str(e)}")
    return text


def analyze_repeated_words(titles):
    words = re.findall(r'\b\w+\b', ' '.join(titles).lower())
    return {w: c for w, c in Counter(words).items() if c >= 2}


def get_article_content(driver):
    try:
        content = driver.find_element(By.ID, "main-content").text
        return content[:1000] + "..." if len(content) > 1000 else content
    except:
        return "❌ No content found"


def download_article_image(driver: WebDriver, idx: int, folder: str = "downloaded_images"):
    try:
        os.makedirs(folder, exist_ok=True)
        img_elem = driver.find_element(By.XPATH, "//article//img | //div[contains(@class,'a_c')]//img")
        img_url = img_elem.get_attribute("src")
        if img_url.startswith("/"):
            img_url = urljoin(driver.current_url, img_url)

        img_data = requests.get(img_url, timeout=10).content
        with open(os.path.join(folder, f"article_{idx}.jpg"), "wb") as f:
            f.write(img_data)
        print(f"✅ Saved image: article_{idx}.jpg")
    except Exception as e:
        print(f"❌ Image download failed for article {idx}: {str(e)}")


# ======== WebDriver Setup ========
def get_browserstack_driver(capabilities):
    options = webdriver.ChromeOptions()
    bstack_options = {
        "os": capabilities.get('os', 'Windows'),
        "osVersion": capabilities.get('osVersion', '10'),
        "local": "false",
        "seleniumVersion": "4.0.0",
        "userName": USERNAME,
        "accessKey": ACCESS_KEY
    }

    if 'deviceName' in capabilities:
        bstack_options['deviceName'] = capabilities['deviceName']
        bstack_options['osVersion'] = capabilities.get('platformVersion', '12.0')
        bstack_options['realMobile'] = 'true'

    options.set_capability('bstack:options', bstack_options)
    options.set_capability('browserName', capabilities.get('browserName', 'chrome'))
    options.set_capability('browserVersion', capabilities.get('browserVersion', 'latest'))

    return webdriver.Remote(
        command_executor=f'https://{USERNAME}:{ACCESS_KEY}@hub-cloud.browserstack.com/wd/hub',
        options=options
    )


# ======== Test Runner ========
def run_test_session(capabilities, local_test=False):
    translated_titles = []
    driver = None

    try:
        if local_test:
            options = ChromeOptions()
            options.add_argument('--lang=es')
            options.add_argument('--disable-notifications')
            driver = webdriver.Chrome(options=options)
            test_name = "Local Chrome"
        else:
            driver = get_browserstack_driver(capabilities)
            test_name = capabilities.get('name', 'BrowserStack Test')

        print(f"\n=== {test_name} ===")
        driver.get("https://elpais.com")

        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            ).click()
        except:
            pass

        try:
            opinion_xpath = "//a[contains(@href,'/opinion/')]"
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, opinion_xpath))
            ).click()
        except:
            print("❌ 'Opinión' section not found")
            return []

        articles = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//article//h2/a"))
        )[:5]

        for idx, article in enumerate(articles, 1):
            try:
                href = article.get_attribute("href")
                driver.execute_script(f"window.open('{href}');")
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(2)

                title = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                ).text
                subheading = driver.find_element(By.XPATH, "//h2").text if driver.find_elements(By.XPATH, "//h2") else "No subheading"
                content = get_article_content(driver)
                translated_title = translate_text(title)

                print(f"\n📰 Article {idx} ({test_name})")
                print(f"Title (ES): {title}")
                print(f"Translated (EN): {translated_title}")
                print(f"Subheading: {subheading}")
                print(f"Content: {content[:200]}...")

                download_article_image(driver, idx)
                translated_titles.append(translated_title)

                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            except Exception as e:
                print(f"❌ Error with article {idx}: {str(e)}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

    finally:
        if driver:
            driver.quit()
    return translated_titles


# ======== Main Runner ========
def main():
    all_titles = run_test_session({}, local_test=True)

    # BrowserStack devices
    browsers = [
        {
            'browserName': 'Chrome',
            'browserVersion': 'latest',
            'os': 'Windows',
            'osVersion': '11',
            'name': 'Windows 11 - Chrome'
        },
        {
            'browserName': 'Edge',
            'browserVersion': 'latest',
            'os': 'Windows',
            'osVersion': '10',
            'name': 'Windows 10 - Edge'
        },
        {
            'browserName': 'Firefox',
            'browserVersion': 'latest',
            'os': 'Windows',
            'osVersion': '10',
            'name': 'Windows 10 - Firefox'
        },
        {
            'browserName': 'Chrome',
            'deviceName': 'Samsung Galaxy S22',
            'platformVersion': '12.0',
            'os': 'Android',
            'name': 'Galaxy S22 - Chrome'
        },
        {
            'browserName': 'Chrome',
            'deviceName': 'Google Pixel 7',
            'platformVersion': '13.0',
            'os': 'Android',
            'name': 'Pixel 7 - Chrome'
        }
    ]

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_test_session, b) for b in browsers]
        for future in futures:
            try:
                titles = future.result()
                all_titles.extend(titles)
            except Exception as e:
                print(f"❌ Parallel test error: {str(e)}")

    # Final word analysis
    repeated = analyze_repeated_words(all_titles)
    print("\n🔍 Repeated Words Summary:")
    for word, count in sorted(repeated.items(), key=lambda x: (-x[1], x[0])):
        print(f"{word}: {count} times")


if __name__ == "__main__":
    main()
