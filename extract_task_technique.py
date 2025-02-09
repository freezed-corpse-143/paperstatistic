import os
import re
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from util import client, extract_from_code_block, extract_json_from_str

os.makedirs("./extract_infomation", exist_ok=True)

extract_task_technique_prompt = '''Please read the input text and follow these instructions:
1. Extract the task name, description, challenges and latent techniques of solution from the input text into the first code block.
2. Extract the techique name, description, advantages, disadvantages, targeted tasks and project urls from the input text into the second code block.
3. The output should be presented within a code block in the following format: "json\n<output>", where "<output>" is the placeholder for the output.

Output examples are as follows:

```json
{
    "name": "<task name placeholder>",
    "description": [],
    "challenges": [],
    "latent_techniques": []
}
```

```json
{
    "name": "<technique name placeholder>",
    "description": [],
    "advantages": [],
    "disadvantages": [],
    "targeted_tasks": [],
    "project_urls": []
}
```
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


def extract_task_technique(input_text):
    global extract_task_technique_prompt, client
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {'role': 'system', 'content': extract_task_technique_prompt},
            {'role': 'user', 'content': f'input text\n{input_text}'}
        ],
        stream=False,
        temperature=0.01
    )
    result = completion.choices[0].message.content
    result_json_list = extract_from_code_block(result)
    if len(result_json_list) > 0:
        task_json_str = result_json_list[0]
        technique_json_str = result_json_list[1]

        task_json = extract_json_from_str(task_json_str)
        technique_json = extract_json_from_str(technique_json_str)
        return task_json, technique_json
    return {}, {}

def merge_task_info(task_list):
    merged_tasks = {}

    for task in task_list:
        name = task["name"]

        if name in merged_tasks:
            for attribute_name in ["description", "challenges", "latent_techniques"]:
                merged_tasks[name][attribute_name] = list(set(merged_tasks[name][attribute_name]+task[attribute_name]))
        else:
            merged_tasks[name] = {
                "name": name,
                "description": list(set(task['description'])),
                "challenges": list(set(task["challenges"])),
                "latent_techniques": list(set(task['latent_techniques']))
            }

    return list(merged_tasks.values())

def merge_technique_info(technique_list):
    merged_techniques = {}

    for technique in technique_list:
        name = technique["name"]

        if name in merged_techniques:
            for attribute_name in ["description", "advantages", "disadvantages", "targeted_tasks", "project_urls"]:
                merged_techniques[name][attribute_name] = list(set(merged_techniques[name][attribute_name]+technique[attribute_name]))
        else:
            merged_techniques[name] = {
                "name": name,
                "description": list(set(technique['description'])),
                "advantages": list(set(technique["advantages"])),
                "disadvantages": list(set(technique["disadvantages"])),
                "targeted_tasks": list(set(technique["targeted_tasks"])),
                "project_urls": list(set(technique['project_urls']))
            }

    return list(merged_techniques.values())

def batch_extract_task_technique_infomation(json_dir):
    task_technique_list = []
    for file_name in os.listdir(json_dir):
        file_path = os.path.join(json_dir, file_name)
        json_data = read_structure_data(file_path)
        task_technique_text = ""
        sn_list = "abstract introduction conclusion limitation".split(" ")
        for sn in sn_list:
            if sn in json_data.keys():
                task_technique_text += json_data[sn] + "\n"
        task_technique_text = task_technique_text.strip("\n")
        task_technique_list.append(task_technique_text)

    task_results = []
    technique_results =[]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(extract_task_technique, input_text) for input_text in task_technique_list]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            task, technique = future.result()
            task_results.append(task)
            technique_results.append(technique)

    merged_task = merge_task_info(task_results)
    merged_technique = merge_technique_info(technique_results)

    if os.path.exists("./extract_infomation/task.json"):
        with open("./extract_infomation/task.json", encoding='utf-8') as f:
            previous_task_infomation = json.load(f)
            merged_task.extend(previous_task_infomation)
            merged_task = merge_task_info(merged_task)

    with open("./extract_infomation/task.json", 'w', encoding='utf-8') as f:
        json.dump(merged_task, f, indent=4)

    if os.path.exists("./extract_infomation/technique.json"):
        with open("./extract_infomation/technique.json", encoding='utf-8') as f:
            previous_technique_infomation = json.load(f)
            merged_technique.extend(previous_technique_infomation)
            merged_technique = merge_technique_info(merged_technique)

    with open("./extract_infomation/technique.json", 'w', encoding='utf-8') as f:
        json.dump(merged_technique, f, indent=4)

def main():
    parser = argparse.ArgumentParser(description="extract task and technique information from JSON files in a directory.")
    parser.add_argument("json_dir", type=str, help="Directory containing JSON files")
    args = parser.parse_args()

    json_dir = args.json_dir

    if not os.path.exists(json_dir):
        print(f"Error: The directory '{json_dir}' does not exist.")
        return

    if not os.path.isdir(json_dir):
        print(f"Error: '{json_dir}' is not a directory.")
        return

    batch_extract_task_technique_infomation(json_dir)

if __name__ == "__main__":
    main()