import os
import re
import json
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
import argparse
client = OpenAI(api_key= os.environ['BAILIAN_API_KEY'] , base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

os.makedirs("./logical_flow", exist_ok=True)

logical_flow_prompt = '''Please read the input text and past writing logic provided in the code block below, and follow these instructions:
1. Determine if the core narrative structure of the input text is already covered in the previous writing frameworks.
2. If not present, create a new writing framework for the input text.
3. Present the new writing framework within a code block using format "```string\n<output>```".
4. Ensure the framework focuses exclusively on compositional patterns, ignoring specific model names, approach names, method names, datasets, numerical results, and technical jargon.
5. Condense the writing framework into a single cohesive paragraph.

```Previous Writing Frameworks
{previous_writing_frameworks}
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

def number_hints_list(hints):
    if len(hints) == 0:
        return ""
    else:
        result = ""
        for idx, h in enumerate(hints):
            result += f"{idx} :{h}\n"
        result = result.strip("\n")
        return result
def generate_logical_flow(text_list, client, prompt, previous_logical_flows_list):
    
    for text in text_list:
        previous_logical_flows = number_hints_list(previous_logical_flows_list)

        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {'role': 'system', 'content': prompt.format(
                    previous_writing_frameworks=previous_logical_flows
                )},
                {'role': 'user', 'content': f'```input text\n{text}```'}
            ],
            stream=False,
            temperature=0.0
        )
        result = completion.choices[0].message.content

        new_logical_flow = extract_from_code_block(result)
        if len(new_logical_flow) != 0:
            new_logical_flow = new_logical_flow[0][len("string\n"):].strip("<").strip(">")
        previous_logical_flows_list.append(new_logical_flow)
    return previous_logical_flows_list


def process_section(sn, json_data_list, client, logical_flow_prompt):
    sn_aggregation = []
    for json_data in json_data_list:
        if sn in json_data.keys():
            sn_aggregation.append(json_data[sn])
    if os.path.exists(f"./logical_flow/{sn}.json"):
        with open(f"./logical_flow/{sn}.json", encoding='utf-8') as f:
            previous_logical_flows_list = json.load(f)
    else:
        previous_logical_flows_list = []

    logical_flow_list = generate_logical_flow(sn_aggregation, client, logical_flow_prompt, previous_logical_flows_list)
    with open(f"./logical_flow/{sn}.json", 'w', encoding='utf-8') as f:
        json.dump(logical_flow_list, f, indent=4)


def batch_generate_logical_flow(json_dir):
    global client, logical_flow_prompt
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

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(process_section, sn, json_data_list, client, logical_flow_prompt)
            for sn in section_name_list
        ]
        for future in futures:
            future.result()

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