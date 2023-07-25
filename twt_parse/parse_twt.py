import json
import os
from dotenv import load_dotenv
from multiprocessing import Pool
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright
from config import VIEWPORT_SIZE, HEADLESS_MODE, STATE_PATH

load_dotenv()

LOGIN = os.getenv('LOGIN')
NICK = os.getenv('NICK')
PASSWORD = os.getenv('PASSWORD')


starts_url = [
    'https://twitter.com/zachxbt',
    'https://twitter.com/tayvano_'
]


def save_results(name_user, sorted_tweet_data):
    file_path = f'data/{name_user}.json'
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)
        for timestamp, tweet_info in sorted_tweet_data.items():
            if timestamp not in existing_data:
                existing_data[timestamp] = tweet_info

        with open(file_path, 'w', encoding='utf-8') as json_file:
            order = OrderedDict(sorted(existing_data.items(),
                                key=lambda x: datetime.strptime(x[0],
                                '%d-%m-%Y %H:%M:%S')))
            json.dump(order, json_file, ensure_ascii=False, indent=4)

    else:
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump(sorted_tweet_data, json_file,
                      ensure_ascii=False, indent=4)


def save_state():
    with sync_playwright() as p:
        engine = p.chromium
        browser = engine.launch(headless=HEADLESS_MODE)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://twitter.com/i/flow/login?redirect_after_login=%2Fhome%3Flang%3Dru")
        page.get_by_label("Номер телефона, адрес электронной "
                          "почты или имя пользователя").click()
        page.get_by_label("Номер телефона, адрес электронной почты "
                          "или имя пользователя").fill(LOGIN)
        page.get_by_role("button", name="Далее").click()
        page.get_by_test_id("ocfEnterTextTextInput").click()
        page.get_by_test_id("ocfEnterTextTextInput").fill(NICK)
        page.get_by_test_id("ocfEnterTextNextButton").click()
        page.get_by_label("Пароль", exact=True).click()
        page.get_by_label("Пароль", exact=True).fill(PASSWORD)
        page.get_by_test_id("LoginForm_Login_Button").click()
        page.wait_for_selector('//*[@id="react-root"]/div/div/div[2]/main/'
                               'div/div/div/div[2]/div/div[2]/div/div/div/'
                               'div[4]/div/section/div/div/div/div/div[2]/'
                               'div/div/h2/div[2]/span')
        context.storage_state(path=STATE_PATH)


def parse_report_item(url):
    with sync_playwright() as p:
        context = (p.chromium.launch(headless=HEADLESS_MODE)
                   .new_context(storage_state=STATE_PATH,
                                viewport=VIEWPORT_SIZE))
        page = context.new_page()
        page.goto(url, wait_until='domcontentloaded')
        page.wait_for_selector('div[data-testid="cellInnerDiv"]')

        tweet_elements = page.query_selector_all(
            'div[data-testid="cellInnerDiv"]')

        tweet_data = {}

        for tweet_element in tweet_elements:
            tweet_text = tweet_element.inner_text()

            tweet_text = tweet_text.replace('\n', '')

            date_time_element = tweet_element.query_selector('time')
            tweet_date = date_time_element.get_attribute(
                'datetime') if date_time_element else None

            moscow_time = None
            if tweet_date:
                parsed_time = datetime.strptime(tweet_date,
                                                '%Y-%m-%dT%H:%M:%S.000Z')
                moscow_time = parsed_time.replace(
                    tzinfo=timezone.utc).astimezone(
                    timezone(timedelta(hours=3)))

            formatted_time = moscow_time.strftime(
                '%d-%m-%Y %H:%M:%S') if moscow_time else None

            tweet_link = tweet_element.query_selector(
                '//*/div[2]/div/div[3]/a')
            tweet_link = tweet_link.get_attribute(
                'href') if tweet_link else None

            if tweet_text.strip() and formatted_time and tweet_link:
                tweet_data[formatted_time] = {
                    'text': tweet_text.strip(),
                    'link': f'https://twitter.com{tweet_link}'
                }

        sorted_tweet_data = OrderedDict(
            sorted(tweet_data.items(),
                   key=lambda x: datetime.strptime(x[0],
                                                   '%d-%m-%Y %H:%M:%S')))
        name_user = url.split('/')[-1]
        save_results(name_user, sorted_tweet_data)


if __name__ == '__main__':
    # save_state()
    p = Pool(processes=len(starts_url))
    tweet_data_list = p.map(parse_report_item, starts_url)
