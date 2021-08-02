import os
import typing
import requests
import tempfile
from typing import List

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
"""
Represents logic for handling interactions with Quizlet.
"""
QUIZLET_HOME_PAGE = "https://quizlet.com"


class Flashcard:
    """A quizlet flashcard. Each flashcard contains a front and back side."""
    def __init__(self, front=None, back=None, back_image_path=None):
        self.front = front
        self.back = back
        self.back_image_path = back_image_path


def scrape_quizlet_flashcards(url: str, username: str, password: str) -> List[Flashcard]:
    """
    Retrieves a list of flashcards from the provided URL.
    :param url: The Quizlet URL to scrape
    :param username: The user name needed to authenticate to quizlet
    :param password: The password needed to authenticate to quizlet
    :return: a list of flashcards, None if an error is encountered.
    """
    with init_chrome_webdriver() as driver:
        authenticate_to_quizlet(driver, username, password)
        driver.get(url)

        wait = WebDriverWait(driver, 10)

        site_element = driver.find_element_by_id('setPageSetDetails')
        actions = ActionChains(driver)
        actions.move_to_element(site_element).perform()

        user_agent = driver.execute_script('return navigator.userAgent')
        terms_list_element = get_elem_wait_by_xpath(wait, "//section[@class='SetPageTerms-termsList']")
        terms = terms_list_element.find_elements_by_class_name('SetPageTerms-term')
        return [_process_term_element(term, user_agent) for term in terms]


def _process_term_element(term: WebElement, user_agent: str) -> Flashcard:
    """
    Helper that makes the HTTP GET request and retrieves the actual text from the quizlet URL
    :param term: The web element that contains all the information about the flashcard
    :param user_agent: A string represent the user agent that the Selenium driver is using
    :return: A string containing all the flashcard data
    """
    flash_card_elem = term.find_element_by_xpath('.//div[@class="SetPageTerm-content"]')
    small_side_elem = flash_card_elem.find_element_by_xpath('./div[@class="SetPageTerm-side SetPageTerm-smallSide"]')
    large_side_elem = flash_card_elem.find_element_by_xpath('./div[@class="SetPageTerm-side SetPageTerm-largeSide"]')
    back, back_image_path = _process_large_side_elem(large_side_elem, user_agent)
    return Flashcard(front=_process_small_side_elem(small_side_elem),
                     back=back,
                     back_image_path=back_image_path)


def _process_small_side_elem(small_side_elem: WebElement) -> str:
    """Processes the small side web element, which is the initial side with text on it"""
    text_elem = small_side_elem.find_element_by_xpath('./div/a/span')
    return text_elem.text


def _process_large_side_elem(large_side_elem: WebElement, user_agent: str) -> (str, typing.Optional[str]):
    """Processes the large side web element, which includes the definition and possibly an image"""
    definition_text = _process_definition_text_elem(large_side_elem)
    image_file_path = _download_image(large_side_elem, user_agent)
    return definition_text, image_file_path


def _process_definition_text_elem(large_side_elem: WebElement) -> str:
    """Processes the definition text of the back side of the flashcard"""
    definition_elem = large_side_elem.find_element_by_xpath(".//a[@class='SetPageTerm-definitionText']")
    text_elem = definition_elem.find_element_by_xpath('./span')
    return text_elem.text


def _image_exists(large_side_elem: WebElement) -> bool:
    return len(large_side_elem.find_elements_by_xpath('.//img')) > 0


def _download_image(large_side_elem: WebElement, user_agent: str) -> typing.Optional[str]:
    if not _image_exists(large_side_elem):
        return None

    img = large_side_elem.find_element_by_xpath('.//img')
    src = img.get_attribute('src')

    resp = requests.get(src, headers={'User-Agent': user_agent})
    if resp.status_code != 200:
        raise ValueError("Could not download image")

    (fd, file_name) = tempfile.mkstemp()
    with os.fdopen(fd, 'wb') as f:
        f.write(resp.content)
    return file_name


def init_chrome_webdriver() -> WebDriver:
    """
    Initializes a chrome webdriver handler to be used for scraping Quizlet's website.
    :return: a Chrome Webdriver instance
    """
    chrome_options = Options()
    # TODO: Figure out why headless doesn't work
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def authenticate_to_quizlet(driver: WebDriver, username: str, password: str) -> None:
    """Attempts to authenticate the web driver to the provided user in order to properly view all cards on a link.
    This is done because Quizlet does not allow users to view all cards in a set until they are logged in."""
    driver.get(QUIZLET_HOME_PAGE)

    wait = WebDriverWait(driver, 10)

    login_button = get_elem_wait_by_xpath(wait, '//div[@class="SiteNavLoginSection"]/button[@aria-label="Log in"]')
    login_button.click()

    def enter_username():
        user_input_form = get_elem_wait_by_xpath(wait, '//input[@id="username"]')
        user_input_form.send_keys(username)

    def enter_password():
        password_input_form = get_elem_wait_by_xpath(wait, '//input[@id="password"]')
        password_input_form.send_keys(password)

    enter_username()
    enter_password()

    authenticate_button = get_elem_wait_by_xpath(wait, '//button[@type="submit" and @aria-label="Log in"]')
    authenticate_button.click()

    wait.until(
        EC.url_matches("{}/latest".format(QUIZLET_HOME_PAGE))
    )


def get_elem_wait_by_xpath(wait: WebDriverWait, xpath_cond: str) -> WebElement:
    """Helper method to extract an element with a waiter to ensure that the element has been loaded"""
    return wait.until(
        EC.presence_of_element_located(
            (By.XPATH, xpath_cond)
        )
    )
