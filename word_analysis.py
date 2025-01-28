import json
import re
from collections import defaultdict
import os
import argparse

def string_update_word_frequencies(string, word_frequencies):
    string = string.lower()
    special_tokens = r"\n "
    string_list = re.split(f'[{special_tokens}]', string)
    string_list = [str for str in string_list if str != "" ]

    for str in string_list:
        word_frequencies[str] += 1
    
    

def json_update_word_frequencies(file_path, word_frequencies):
    with open(file_path, encoding='utf-8') as f:
        file_data = json.load(f)
    for key_1 in file_data.keys():
        item_1 = file_data[key_1]

        for subitem in item_1:
            if isinstance(subitem, str):
                string_update_word_frequencies(subitem, word_frequencies)
            elif isinstance(subitem, list):
                for item_2 in subitem:
                    string_update_word_frequencies(item_2, word_frequencies)

def filter_words_frequences(word_frequencies):
    skip_start_tokens = list(r"–#-&0123456789[]<:")
    skip_end_tokens = list(":;?")
    skip_in_tokens = list(r"+˜$¨´,{}|×ł“”‘’—†‡•()∈♢♣@./=_®\\/")
    # skip_in_tokens.extend(list("-abcdefg"))
    new_word_frequencies = defaultdict(int)
    for key in word_frequencies.keys():
        skip = False
        for token in skip_start_tokens:
            if key.startswith(token):
                skip = True
                break
        for token in skip_end_tokens:
            if key.endswith(token):
                skip = True
                break
        for token in skip_in_tokens:
            if token in key:
                skip = True
                break
        if key.endswith("com"):
            skip = True
        if key.startswith("http"):
            skip = True
        if not skip:
            new_word_frequencies[key] = word_frequencies[key]
    return new_word_frequencies

def dir_update_word_frequencies(dir_path, stop_words_path="./stop_words_english.txt", current_words_path ="./current_words.txt"):
    word_frequencies = defaultdict(int)
    files_list = os.listdir(dir_path)
    for file_path in files_list:
        file_path = os.path.join(dir_path, file_path)
        json_update_word_frequencies(file_path, word_frequencies)

    word_frequencies = filter_words_frequences(word_frequencies)

    with open(stop_words_path, encoding='utf-8') as f:
        stop_words = f.read().split("\n")
    
    with open(current_words_path, encoding='utf-8') as f:
        current_words = f.read().split('\n')

    stop_words_count = 0
    current_words_count = 0
    new_word_frequencies = defaultdict(int)
    for key in word_frequencies.keys():
        if key in stop_words:
            stop_words_count += 1
            continue
        if key in current_words:
            current_words_count += 1
            continue
        new_word_frequencies[key] = word_frequencies[key]
    new_word_frequencies = sorted(new_word_frequencies, key=lambda x:x[0])
    new_words_count = len(new_word_frequencies)

    print(f"words statistics: {stop_words_count} words in stop-words, {current_words_count} words in current-words, {new_words_count} new words.")

    with open("./new_words.txt", 'w', encoding='utf-8') as f:
        for w in new_word_frequencies:
            f.write(w+"\n")
    
def main():
    parser = argparse.ArgumentParser(description="Word frequency analysis from JSON files in a directory.")
    parser.add_argument("dir_path", type=str, help="Directory path containing JSON files.")
    parser.add_argument("--stop_words_path", type=str, default="./stop_words_english.txt", help="Path to the stop words file.")
    parser.add_argument("--current_words_path", type=str, default="./current_words.txt", help="Path to the current words file.")
    
    args = parser.parse_args()

    # Check if paths exist
    if not os.path.exists(args.dir_path):
        print(f"Error: Directory path '{args.dir_path}' does not exist.")
        return
    if not os.path.exists(args.stop_words_path):
        print(f"Error: Stop words file '{args.stop_words_path}' does not exist.")
        return
    if not os.path.exists(args.current_words_path):
        print(f"Error: Current words file '{args.current_words_path}' does not exist.")
        return

    # Execute the function
    dir_update_word_frequencies(args.dir_path, args.stop_words_path, args.current_words_path)

if __name__ == "__main__":
    main()