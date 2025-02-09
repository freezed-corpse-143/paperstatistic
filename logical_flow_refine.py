import os
import re
import json
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import argparse
from util import client, extract_from_code_block, extract_json_from_str

os.makedirs("./logical_flow", exist_ok=True)

logical_flow_prompt = '''Please read the input text, and follow these instructions:
1. Create a new writing framework for the input text.
2. Present the new writing framework point by point within a code block using format "```string\n<output>```", where "<output>" is a placeholder.
3. Ensure the framework focuses exclusively on compositional patterns, ignoring specific model names, approach names, method names, datasets, numerical results, and technical jargon.
4. Condense the writing framework into a single cohesive paragraph.
5. An example is as follows:

```string
1. Fistly, the introduction highlights ... . 
2. Then, the focus shifts to ... .  
3. Then, ... .  
...
x. The conclusion emphasizes xxx .
```
'''

fusion_prompt = '''Please read the input json, and follow these instructions:
1. Remove duplicates in input json and refine the input json for more abstract write frameworks with fewer elements.
2. Answer should be in the format of "```json<output>```", where "<output>" is the placeholder of a list.
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

def process_section(text):
    global client, logical_flow_prompt
    completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {'role': 'system', 'content': logical_flow_prompt},
                {'role': 'user', 'content': f'```input text\n{text}```'}
            ],
            stream=False,
            temperature=0.0
        )
    result = completion.choices[0].message.content
    result_str_list = extract_from_code_block(result)
    result_str = result_str_list[0].strip("string\n").strip("<").strip(">")
    return result_str

def fusion_logical_flow(text_list):
    global client, fusion_prompt
    completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {'role': 'system', 'content': fusion_prompt},
                {'role': 'user', 'content': f'```json\n{json.dumps(text_list)}```'}
            ],
            stream=False,
            temperature=0.0
        )
    result = completion.choices[0].message.content
    result_str_list = extract_from_code_block(result)
    result_json = extract_json_from_str(result_str_list[0])
    return result_json

def batch_generate_logical_flow(json_dir):
    json_data_list = []
    for file_name in os.listdir(json_dir):
        file_path = os.path.join(json_dir, file_name)
        json_data_list.append(
            read_structure_data(file_path)
        )
    section_name_list = [
        "abstract",
        "introduction",
        "related_work",
        "experiment",
        "conclusion",
        "appendix"
    ]

    input_data  = []
    for section_name in section_name_list:
        for json_data in json_data_list:
            if section_name in json_data.keys():
                input_data.append((section_name, json_data[section_name]))

    logical_flow_result = defaultdict(list)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures_key = {
            executor.submit(process_section, item[1]):item[0]
            for item in input_data
        }
        for future in futures_key:
            sn = futures_key[future]
            logical_flow_result[sn].append(future.result())
    
    output_flow_result = defaultdict(list)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures_key = {
            executor.submit(fusion_logical_flow, logical_flow_result[sn]):sn
            for sn in logical_flow_result
        }
        for future in futures_key:
            sn = futures_key[future]
            output_flow_result[sn].extend(future.result())

    for sn in output_flow_result:
        with open(f"./logical_flow/{sn}.json", 'w', encoding='utf-8') as f:
            json.dump(output_flow_result[sn], f, indent=4)

def main():
    parser = argparse.ArgumentParser(description="Generate logical flow from JSON files in a directory.")
    parser.add_argument("json_dir", type=str, help="Directory containing JSON files")
    args = parser.parse_args()

    json_dir = args.json_dir

    if not os.path.exists(json_dir):
        print(f"Error: The directory '{json_dir}' does not exist.")
        return

    if not os.path.isdir(json_dir):
        print(f"Error: '{json_dir}' is not a directory.")
        return

    batch_generate_logical_flow(json_dir)

if __name__ == "__main__":
    main()