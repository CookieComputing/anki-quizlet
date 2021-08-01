from typing import List, ByteString

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
"""
Represents logic for handling interactions with Quizlet.
"""


class Flashcard:
    """A quizlet flashcard. Each flashcard contains a front and back side."""
    def __init__(self, front=None, back=None):
        self.front = front
        self.back = back


def scrape_quizlet_flashcards(url: str) -> List[Flashcard]:
    """
    Retrieves a list of flashcards from the provided URL.
    :param url: The Quizlet URL to scrape
    :return: a list of flashcards, None if an error is encountered.
    """
    with init_chrome_webdriver(url) as driver:
        site_element = driver.find_element_by_id('setPageSetDetails')
        actions = ActionChains(driver)
        actions.move_to_element(site_element).perform()

        wait = WebDriverWait(driver, 10)
        terms_list_element = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//section[@class='SetPageTerms-termsList']")))
        terms = terms_list_element.find_elements_by_class_name('SetPageTerms-term')
        return [_process_term_element(term) for term in terms]


def _process_term_element(term: WebElement) -> Flashcard:
    """
    Helper that makes the HTTP GET request and retrieves the actual text from the quizlet URL
    :param url:
    :return: A string containing all the flashcard data
    """
    # flash_card_elem = term.find_element_by_xpath('./div/div/div[2]/div')
    flash_card_elem = term.find_element_by_xpath('.//div[@class="SetPageTerm-content"]')
    small_side_elem = flash_card_elem.find_element_by_xpath('./div[@class="SetPageTerm-side SetPageTerm-smallSide"]')
    large_side_elem = flash_card_elem.find_element_by_xpath('./div[@class="SetPageTerm-side SetPageTerm-largeSide"]')
    return Flashcard(front=_process_small_side_elem(small_side_elem), back=_process_large_side_elem(large_side_elem))


def _process_small_side_elem(small_side_elem: WebElement) -> str:
    """Processes the small side web element, which is the initial side with text on it"""
    text_elem = small_side_elem.find_element_by_xpath('./div/a/span')
    return text_elem.text


def _process_large_side_elem(large_side_elem: WebElement) -> str:
    """Processes the large side web element, which includes the definition and possibly an image"""
    # TODO: Add support for images on larger card side
    definition_elem = large_side_elem.find_element_by_xpath(".//a[@class='SetPageTerm-definitionText']")
    text_elem = definition_elem.find_element_by_xpath('./span')
    return text_elem.text


def init_chrome_webdriver(url: str) -> webdriver:
    """
    Initializes a chrome webdriver handler to be used for scraping Quizlet's website.
    :param url:
    :return: a Chrome Webdriver instance pointing to the provided URL
    """
    chrome_options = Options()
    # TODO: Figure out why headless doesn't work
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome()
    driver.get(url)
    return driver
