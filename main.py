from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from datetime import date
import json, os, requests, pickle, time

WORDS_URI = "https://raw.githubusercontent.com/almgru/svenska-ord.txt/master/svenska-ord.json"
GAME_URI = "https://rabbel.se/"


def load_letters_from_cache(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as file:
            return split_into_sublists(pickle.load(file))
    else:
        return None


def create_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)


def get_filename(ending=".cache"):
    return f"cache\\{date.today()}{ending}"


def save_letters_to_cache(letters, cache_file):
    create_folder("cache")
    with open(cache_file, 'wb') as file:
        pickle.dump(letters, file)


def split_into_sublists(letters):
    letters = [letter.lower() for letter in letters]
    return [letters[i:i+MAX_LEN_COL] for i in range(0, len(letters), MAX_LEN_COL)]


def strip_json_info(list):
    list = f"{list}".replace('[', '').replace(']', '').replace("'", '')
    return list


def get_letters_from_website():
    letters = load_letters_from_cache(TODAYS_CACHE_FILE)
    if letters is not None:
        return letters

    response = requests.get(GAME_URI)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content.decode('utf-8'), 'html.parser')
        hitbox_elements = soup.find_all(class_='tile-hitbox')
        letters = [element.text.strip() for element in hitbox_elements]
        save_letters_to_cache(letters, TODAYS_CACHE_FILE)
        return split_into_sublists(letters)
    else:
        print(f"Failed to fetch webpage. Status code: {response.status_code}")
        return []


MAX_LEN_WORD = 3
MIN_LEN_WORD = 3
MAX_LEN_COL = 4
TODAYS_FACIT_CACHE_FILE = get_filename(".facit.cache")
TODAYS_CACHE_FILE = get_filename()
TODAYS_LETTERS = get_letters_from_website()
WORDS_FILE = 'words.json'



def get_expected_count():
    result_list = []
    if os.path.exists(TODAYS_FACIT_CACHE_FILE):
        return load_facit_cache()
    response = requests.get(GAME_URI)
    soup = BeautifulSoup(response.text, 'html.parser')

    divs = soup.find_all('div', class_='letter-count')
    for div in divs:
        letter_count = int(div.get_text().split()[0])
        words_left = int(div.find_next_sibling(
            class_='words-left').get_text().split()[0])
        result_list.append([letter_count, words_left])
    with open(TODAYS_FACIT_CACHE_FILE, 'wb') as f:
        pickle.dump(result_list, f)
    calc_max_len_word()
    return result_list


def calc_max_len_word():
    global MAX_LEN_WORD
    facit = load_facit_cache()
    for arr in facit:
        if arr[0] > MAX_LEN_WORD:
            MAX_LEN_WORD = arr[0]
    return None


def load_facit_cache():
    try:
        with open(TODAYS_FACIT_CACHE_FILE, 'rb') as f:
            data = pickle.load(f)
        return data
    except FileNotFoundError:
        print("Cache file not found.")
        return None


def load_word_list(file_path):
    global MAX_LEN_WORD
    with open(file_path, 'r', encoding='utf-8') as file:
        word_list = json.load(file)
    word_list = set(word for word in word_list if MIN_LEN_WORD <= len(word) <= MAX_LEN_WORD and word.isalpha())
    return word_list


def download_word_list():
    if os.path.exists(WORDS_FILE):
        return load_word_list(WORDS_FILE)

    response = requests.get(WORDS_URI)

    if response.status_code == 200:
        with open(WORDS_FILE, 'wb') as file:
            file.write(response.content)
    else:
        print(f"Failed to download file. Status code: {response.status_code}")

    return load_word_list(WORDS_FILE)


def is_valid_move(row1, col1, row2, col2):
    return abs(row1 - row2) <= 1 and abs(col1 - col2) <= 1 and (row1 != row2 or col1 != col2)


def find_words(grid, word_list, start_row, start_col, found_words, depth=7):
    stack = [(start_row, start_col, "", set(), 0)]
    while stack:
        row, col, prefix, visited, current_depth = stack.pop()
        prefix += grid[row][col]
        if prefix in word_list and prefix not in found_words:
            found_words.add(prefix)
        visited.add((row, col))
        if current_depth < depth:
            for i in range(max(0, row - 1), min(row + 2, len(grid))):
                for j in range(max(0, col - 1), min(col + 2, len(grid[0]))):
                    if is_valid_move(row, col, i, j) and (i, j) not in visited:
                        stack.append(
                            (i, j, prefix, visited.copy(), current_depth + 1))


def ruin_all_the_fun(grid):
    found_words = set()
    word_list = download_word_list()
    with ThreadPoolExecutor() as executor:
        for row in range(len(grid)):
            for col in range(len(grid[0])):
                executor.submit(find_words, grid, word_list,
                                row, col, found_words)

    categorized_results = {}
    for word in found_words:
        length = len(word)
        if length not in categorized_results:
            categorized_results[length] = []
        categorized_results[length].append(word)

    for words in categorized_results.values():
        words.sort()

    return categorized_results


def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')


def format_to_ascii_table(input_string):
    data = [cell.strip() for cell in input_string.split(',')]
    num_columns = MAX_LEN_COL
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
        formatted_row += f"{table_separator}\n| {' | '.join(cell.ljust(width) for cell, width in zip(row, col_widths))} |\n"
    return formatted_row.upper() + table_separator + "\n"


clear_terminal()
get_expected_count()
calc_max_len_word()
print(f"Giltighet avser om antal ord som hittats stämmer med vad sidan önskar av oss.\n\nDina bokstäver idag: {format_to_ascii_table(strip_json_info(TODAYS_LETTERS))}")
start_time = time.time()
result = ruin_all_the_fun(TODAYS_LETTERS)
execution_time = time.time() - start_time

todays_facit = load_facit_cache()
index = 0
for length, words in sorted(result.items()):
    print(f"{length} bokstäver\n{strip_json_info(words)}\n{len(words)}/{todays_facit[index][1]} ord\n")
    index += 1

print(f"Längsta ordet idag var {MAX_LEN_WORD} bokstäver.\nDenna beräkning tog: {execution_time} sekunder")