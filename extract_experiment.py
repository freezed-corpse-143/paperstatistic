import os
import re
import json
import argparse

os.makedirs("./extract_info", exist_ok=True)

reformat_json_prompt = '''Please convert invalid input json to valid json.
The output should be presented within a code block in the following format: "json\n<output>", where "<output>" is the placeholder for the output.
'''

extract_experiment_prompt = '''Please read the input text and the past experiment information provided below, and follow these instructions:
1. Extract the experiment types (e.g., ablation studies, hyperparameter tuning, etc.), baselines, benchmarks, and metrics from the input text, and integrate them into the past experiment information.
2. The output should be presented within a code block in the following format: "json\n<output>", where "<output>" is the placeholder for the output.

```previous experiment infomation
{previous_experiment_information}
```
'''

def extract_from_code_block(text):
    matches = re.findall(r'```(.*?)```', text, re.DOTALL)
    if matches:
        return [match.strip() for match in matches]
    else:
        print("No code blocks found")
        return []
    
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

def reformat_json(text):
    global reformat_json_prompt
    completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {'role': 'system', 'content': reformat_json_prompt},
                {'role': 'user', 'content': f'```input json\n{text}```'}
            ],
            stream=False,
            temperature=0.0
        )
    
    result = completion.choices[0].message.content
    new_result = extract_from_code_block(result)[0].strip("json").strip("<").strip(">")
    return json.loads(new_result)

def batch_extract_experiment_infomation(json_dir):
    global extract_experiment_prompt, client
    experiment_data_list = []
    for file_name in os.listdir(json_dir):
        file_path = os.path.join(json_dir, file_name)
        json_data = read_structure_data(file_path)
        if "experiment" in json_data.keys():
            experiment_data_list.append(
                json_data['experiment']
            )
    if os.path.exists("./extract_info/experiment.json"):
        with open("./extract_info/experiment.json", encoding='utf-8') as f:
            previous_experiment_infomation = json.load(f)
    else:
        previous_experiment_infomation = {
            "experiment_types": [],
            "baselines": [],
            "benchmarks": [],
            "metrics": [],
        }
    
    for input_text in experiment_data_list:
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {'role': 'system', 'content': extract_experiment_prompt.format(
                    previous_experiment_information=json.dumps(previous_experiment_infomation)
                )},
                {'role': 'user', 'content': f'```input text\n{input_text}```'}
            ],
            stream=False,
            temperature=0.0
        )
        result = completion.choices[0].message.content
        new_experiment_infomation = extract_from_code_block(result)
        if len(new_experiment_infomation) > 0:
            new_experiment_infomation = new_experiment_infomation[0].strip("json").strip("<").strip(">")

            try:
                new_experiment_json = json.loads(new_experiment_infomation)
            except Exception as e:
                print(f"Exception :{e}", new_experiment_infomation)
                with open("./temp/error.txt", 'w', encoding='utf-8') as f:
                    f.write(new_experiment_infomation)
                new_experiment_json = reformat_json(new_experiment_infomation)
            previous_experiment_infomation = new_experiment_json
    
    with open("./extract_info/experiment.json", 'w', encoding='utf-8') as f:
            json.dump(previous_experiment_infomation, f, indent = 4)

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