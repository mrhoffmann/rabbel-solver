from concurrent.futures import ThreadPoolExecutor
import re
import json
import os
import pickle
import time
from datetime import date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyperclip
from bs4 import BeautifulSoup
import requests


WORDS_URI = "https://raw.githubusercontent.com/almgru/svenska-ord.txt/master/svenska-ord.json"
GAME_URI = "https://rabbel.se/"
TODAYS_DATE = None
MIN_LEN_WORD = 3
WORDS_FILE = 'words.json'


def load_letters_from_cache():
    """Getter for the letter-cache

    Returns:
        A multidimensional str array: An array of array sublists in format of 4 x 4
    """
    file_name = get_filename()
    if os.path.exists(file_name):
        with open(file_name, 'rb') as file:
            return split_into_sublists(pickle.load(file))
    else:
        return None


def create_folder(folder_name):
    """Create a folder on the file system

    Args:
        folder_name (str): The desired folder name
    """
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)


def get_todays_date():
    """Getter for todays date

    Returns:
        str: Todays date
    """
    return date.today()


def get_filename(ending=".cache"):
    """Getter for filename

    Args:
        ending (str, optional): Formats the filename you're expected to get. Defaults to ".cache".
        Filenames are expected to follow the format: cache\\DATE<ending>, 
        an example: cache\\2024-02-24.facit.cache or cache\\2024-02-24.cache
    Returns:
        String: filename
    """
    global TODAYS_DATE
    if TODAYS_DATE is None:
        TODAYS_DATE = get_todays_date()
    return f"cache\\{TODAYS_DATE}{ending}"


def save_letters_to_cache(letters, cache_file):
    """Setter for letter cache

    Args:
        letters (_type_): _description_
        cache_file (_type_): _description_
    """
    create_folder("cache")
    with open(cache_file, 'wb') as file:
        pickle.dump(letters, file)


def split_into_sublists(letters):
    """Split a larger array of letters into multi dimensional arrays

    Args:
        letters (str array): an str array of expected size 16

    Returns:
        _type_: _description_
    """
    if len(letters) != 16:
        print("ERROR: Invalid array size")
    letters = [letter.lower() for letter in letters]
    return [letters[i:i+4] for i in range(0, len(letters), 4)]


def strip_json_info(input_list):
    """Getter for a string representation of an array

    Args:
        input_list (any array): Any array you want to display as: item, item1, item2, item3

    Returns:
        str: comma-separated items of the array
    """
    input_list = f"{input_list}".replace(
        '[', '').replace(']', '').replace("'", '')
    return input_list


def get_letters_from_website():
    """Getter used to download letters from the site

    Returns:
        an str multidimensional array: The letters in a 4x4 array
    """

    letters = load_letters_from_cache()
    if letters is not None:
        return letters
    driver = webdriver.Firefox()

    try:
        driver.get(GAME_URI)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "tile-hitbox"))
        )

        page_source = driver.page_source
        driver.quit()
        soup = BeautifulSoup(page_source, 'html.parser')
        hitbox_elements = soup.find_all(class_='tile-hitbox')
        letters = [element.text.strip() for element in hitbox_elements]
        save_letters_to_cache(letters, get_filename())

        return split_into_sublists(letters)
    except Exception as e:
        print(f"ERROR: {e}")
        return []


MAX_LEN_WORD = 3
TODAYS_FACIT_CACHE_FILE = get_filename(".facit.cache")
TODAYS_CACHE_FILE = get_filename()


def get_expected_count():
    """Getter for fetching the N-letter word rules for the cache

    Returns:
        str array: What N-letter words to solve today
    """
    result_list = []
    if os.path.exists(get_filename(".facit.cache")):
        return load_facit_cache()

    driver = webdriver.Firefox()

    try:
        driver.get(GAME_URI)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "letter-count"))
        )

        page_source = driver.page_source
        driver.quit()
        soup = BeautifulSoup(page_source, 'html.parser')
        divs = soup.find_all('div', class_='letter-count')
        for div in divs:
            letter_count = int(div.get_text().split()[0])
            words_left = int(div.find_next_sibling(
                class_='words-left').get_text().split()[0])
            result_list.append([letter_count, words_left])

        with open(get_filename(".facit.cache"), 'wb') as f:
            pickle.dump(result_list, f)

        calc_max_len_word()
        return result_list
    except Exception as e:
        print(f"ERROR: {e}")
        return []


def calc_max_len_word():
    """Calculate what the longest word is for the active date. Used to limit the 
    number of traversing made in find_words.

    Returns:
        int: What the longest word of the date is
    """
    global MAX_LEN_WORD
    facit = load_facit_cache()
    for arr in facit:
        if arr[0] > MAX_LEN_WORD:
            MAX_LEN_WORD = arr[0]
    return MAX_LEN_WORD


def load_facit_cache():
    """Getter for facit cache

    Returns:
        str array: An str array of what N-letter words to solve today
    """
    try:
        with open(get_filename(".facit.cache"), 'rb') as f:
            data = pickle.load(f)
        return data
    except FileNotFoundError:
        print("Cache file not found.")
        return None


def load_word_list(file_path):
    """Getter for words-file

    Args:
        file_path (str): The file to load words from.

    Returns:
        str array: The words that may be traversed
    """
    global MAX_LEN_WORD
    with open(file_path, 'r', encoding='utf-8') as file:
        word_list = json.load(file)
    word_list = set(word for word in word_list if MIN_LEN_WORD <=
                    len(word) <= MAX_LEN_WORD and word.isalpha())
    return word_list


def download_word_list():
    """Getter for downloading all the words to traverse.

    Returns:
        str array: The words that may be traversed
    """
    if os.path.exists(WORDS_FILE):
        return load_word_list(WORDS_FILE)

    response = requests.get(WORDS_URI, timeout=32)

    if response.status_code == 200:
        with open(WORDS_FILE, 'wb') as file:
            file.write(response.content)
    else:
        print(f"ERROR: Failed to download file. Status code: {
            response.status_code}")

    return load_word_list(WORDS_FILE)


def is_valid_move(row1, col1, row2, col2):
    """Checks if a move from one position to another on a grid is valid.

    Parameters:
    - row1 (int): The row index of the starting position.
    - col1 (int): The column index of the starting position.
    - row2 (int): The row index of the destination position.
    - col2 (int): The column index of the destination position.

    Returns:
    - bool: True if the move is valid, False otherwise.
    """
    return abs(row1 - row2) <= 1 and abs(col1 - col2) <= 1 and (row1 != row2 or col1 != col2)


def find_words(grid, word_list, start_row, start_col, found_words):
    """Traverse the letter grid to determine what words can be found

    Args:
        grid (str multidimensional array): Letters available in a 4x4 grid
        word_list (str array): What words are available to match against
        start_row (int): Starting row
        start_col (int): Starting column
        found_words (str array): What words has been found
    """
    stack = [(start_row, start_col, "", set(), 0)]
    while stack:
        row, col, prefix, visited, current_depth = stack.pop()
        prefix += grid[row][col]
        if prefix in word_list and prefix not in found_words:
            found_words.add(prefix)
        visited.add((row, col))
        if current_depth < MAX_LEN_WORD:
            for i in range(max(0, row - 1), min(row + 2, len(grid))):
                for j in range(max(0, col - 1), min(col + 2, len(grid[0]))):
                    if is_valid_move(row, col, i, j) and (i, j) not in visited:
                        stack.append(
                            (i, j, prefix, visited.copy(), current_depth + 1))


def ruin_all_the_fun(grid):
    """This will help you ruin the fun of the game.

    Args:
        grid (An str multidimensional array of letters): The 4x4 letter multidimensional 
        array to traverse

    Returns:
        str multidimensional array: categorized results depending on the N-letter words on the site
    """
    found_words = set()
    word_list = download_word_list()
    with ThreadPoolExecutor() as executor:
        for row in range(len(grid)):
            for col in range(len(grid[0])):
                executor.submit(find_words, grid, word_list,
                                row, col, found_words)

    categorized_results = {}
    for word in found_words:
        lengths = len(word)
        if lengths not in categorized_results:
            categorized_results[lengths] = []
        categorized_results[lengths].append(word)

    for categorized_result in categorized_results.values():
        categorized_result.sort()

    return categorized_results


def clear_terminal():
    """Clean the terminal to make it more readable to the end user
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def format_to_ascii_table(input_string):
    """Formatter for letters to turn them into an ascii-table of 4x4

    Args:
        input_string (_type_): _description_

    Returns:
        _type_: _description_
    """
    data = [cell.strip() for cell in input_string.split(',')]
    num_columns = 4
    num_rows = -(-len(data) // num_columns)

    table = []
    for i in range(num_rows):
        start_index = i * num_columns
        end_index = min((i + 1) * num_columns, len(data))
        row = data[start_index:end_index]
        table.append(row)

    col_widths = [max(len(cell) for cell in col) for col in zip(*table)]
    formatted_row = "\n"
    table_separator = "+---+---+---+---+"
    for row in table:
        formatted_row += f"{table_separator}\n| {' | '.join(
            cell.ljust(width) for cell, width in zip(row, col_widths))} |\n"
    return formatted_row.upper() + table_separator + "\n"


def is_valid_date(date_string):
    """Validator for a string representation of a date

    Args:
        date_string (str): A date formatted YYYY-MM-dd

    Returns:
        boolean: true or false
    """
    # Regular expression pattern for YYYY-MM-dd format
    pattern = r'^\d{4}-\d{2}-\d{2}$'

    # Check if the input matches the pattern
    if re.match(pattern, date_string):
        return True
    return False


def tackle_user_input():
    """Help handle user input of date
    """
    global TODAYS_DATE
    user_input = input(
        f"Ange ett datum du vill köra (tryck bara Enter för {get_todays_date()}): ")

    if is_valid_date(user_input):
        TODAYS_DATE = user_input
    else:
        TODAYS_DATE = get_todays_date()


def is_date_today():
    """Determine if the date is todays date or not

    Returns:
        str: Human readable representation of the date
    """
    if TODAYS_DATE == get_todays_date():
        return "idag"
    return TODAYS_DATE


def main():
    index = 0
    total_points = 0
    total_words = 0
    clear_terminal()
    create_folder("cache")
    tackle_user_input()
    get_expected_count()
    calc_max_len_word()
    TODAYS_LETTERS = get_letters_from_website()
    print(f"\nDina bokstäver {is_date_today()}: {
        format_to_ascii_table(strip_json_info(TODAYS_LETTERS))}")
    start_time = time.time()
    result = ruin_all_the_fun(TODAYS_LETTERS)
    execution_time = time.time() - start_time

    todays_facit = load_facit_cache()
    for length, words in sorted(result.items()):
        word_len = len(words)
        print(f"{length} bokstäver\n{strip_json_info(words)}\n{
            word_len}/{todays_facit[index][1]} ord\n")

        if length == 3:
            total_points += word_len
        if length == 4:
            total_points += word_len * 2
        if length == 5:
            total_points += word_len * 3
        if length == 6:
            total_points += word_len * 5
        if length == 7:
            total_points += word_len * 8
        if length == 8:
            total_points += word_len * 11

        total_words += word_len
        index += 1

    storage_cache = []
    for word in result.items():
        storage_cache += word[1]

    print(strip_json_info(storage_cache))

    result_format = f"#Rabbel #{TODAYS_DATE}\n{
        total_words}/{total_words} ord, {total_points} poäng\nhttps://rabbel.se"

    pyperclip.copy(result_format)
    print(result_format)

    print(f"\nLängsta ordet idag var {
        MAX_LEN_WORD} bokstäver.\nDenna beräkning tog: {execution_time} sekunder")
    input("Tryck valfri knapp för att avsluta...")


if __name__ == "__main__":
    main()
