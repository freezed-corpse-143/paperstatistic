import os
import re
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from util import client, extract_from_code_block, extract_json_from_str

os.makedirs("./extract_infomation", exist_ok=True)


extract_experiment_prompt = '''Please read the input text and follow these instructions:
1. Extract the experiment types (e.g., ablation studies, hyperparameter tuning, etc.), baselines, benchmarks, and metrics from the input text.
2. The output should be presented within a code block in the following format: "json\n<output>", where "<output>" is the placeholder for the output.
'''
    
def concatenate_values(structure):
    result = []
    if isinstance(structure, str):
        result.append(structure)
    if isinstance(structure, list):
        if len(structure) != 0:
            for v in structure:
                result.append(concatenate_values(v))
    if isinstance(structure, dict):
        if len(structure.values()) != 0:
            for v in structure.values():
                result.append(concatenate_values(v))
    result = [item for item in result if item is not None]
    return "\n".join(result)
    
def read_structure_data(json_path):
    section_name_list = [
        "title",
        "abstract",
        "introduction",
        "related work",
        "experiment",
        "conclusion",
        "limitation",
        "reference",
        "appendix",
        "checklist",
        "image",
        "table",
    ]
    with open(json_path, encoding='utf-8') as f:
        json_data = json.load(f)
    new_json_data = dict()
    for key in json_data['structure'].keys():
        for sn in section_name_list:
            if sn in key.lower():
                new_json_data[sn] = concatenate_values(json_data['structure'][key])
    empty_key_list = []
    for key in new_json_data.keys():
        value_idx_list = new_json_data[key].split("\n")
        value_list = []
        for idx in value_idx_list:
            if idx != "":
                value_list.append(json_data['data'][idx])
        new_json_data[key] = "\n".join(value_list)
        if new_json_data[key] == "":
            empty_key_list.append(key)
    for key in empty_key_list:
        new_json_data.pop(key)
    if "related work" in new_json_data.keys():
        new_json_data['related_work'] = new_json_data['related work']
        new_json_data.pop("related work")
    return new_json_data


def extract_experiment_info(input_text):
    global extract_experiment_prompt, client
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {'role': 'system', 'content': extract_experiment_prompt},
            {'role': 'user', 'content': f'input text\n{input_text}'}
        ],
        stream=False,
        temperature=0.01
    )
    result = completion.choices[0].message.content
    result_str_list = extract_from_code_block(result)
    if len(result_str_list) > 0:
        result_str = result_str_list[0]
        result_json = extract_json_from_str(result_str)
        return result_json
    return {}

def merge_experiment_info(experiment_list):
    merged_experiment = {
        "experiment_types": set(),
        "baselines": set(),
        "benchmarks": set(),
        "metrics": set(),
    }
    for experiment in experiment_list:
        for key in merged_experiment.keys():
            if key in experiment:
                merged_experiment[key].update(experiment[key])
    
    for key in merged_experiment:
        merged_experiment[key] = list(merged_experiment[key])
    
    return merged_experiment

def batch_extract_experiment_infomation(json_dir):
    experiment_data_list = []
    for file_name in os.listdir(json_dir):
        file_path = os.path.join(json_dir, file_name)
        json_data = read_structure_data(file_path)
        if "experiment" in json_data.keys():
            experiment_data_list.append(json_data['experiment'])

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(extract_experiment_info, input_text) for input_text in experiment_data_list]
        experiment_results = [future.result() for future in as_completed(futures)]

    merged_experiment = merge_experiment_info(experiment_results)

    if os.path.exists("./extract_infomation/experiment.json"):
        with open("./extract_infomation/experiment.json", encoding='utf-8') as f:
            previous_experiment_infomation = json.load(f)
        merged_experiment = merge_experiment_info([previous_experiment_infomation, merged_experiment])

    with open("./extract_infomation/experiment.json", 'w', encoding='utf-8') as f:
        json.dump(merged_experiment, f, indent=4)

def main():
    parser = argparse.ArgumentParser(description="extract experiment information from JSON files in a directory.")
    parser.add_argument("json_dir", type=str, help="Directory containing JSON files")
    args = parser.parse_args()

    json_dir = args.json_dir

    if not os.path.exists(json_dir):
        print(f"Error: The directory '{json_dir}' does not exist.")
        return

    if not os.path.isdir(json_dir):
        print(f"Error: '{json_dir}' is not a directory.")
        return

    batch_extract_experiment_infomation(json_dir)

if __name__ == "__main__":
    main()