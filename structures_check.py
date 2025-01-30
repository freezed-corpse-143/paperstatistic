import os
import json
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import argparse

client = OpenAI(
    api_key= os.environ['BAILIAN_API_KEY'], 
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

reshape_prompt = '''Please modify the structure of each dictionary in the provided list according to the following requirements:
1. Ensure that the top-level nodes only include the following:
    - Title
    - Abstract
    - Introduction
    - Related Work
    - Method
    - Experiments
    - Conclusion
    - Limitations
    - References
    - Appendix
    - checlist
    - image
    - table
2. Move any other content into the appropriate top-level node as a sub-node.
3. Output the modified structure in a code block for clarity, which is in the format of "```json\n{output}```".
'''

reformat_json_prompt = '''Please convert invalid input json to valid json.
The output should be presented within a code block in the following format: "json\n<output>", where "<output>" is the placeholder for the output.
'''

os.makedirs("./structures", exist_ok=True)


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

def check_json_structures(json_dir):
    structures = []
    json_name_list = os.listdir(json_dir)
    for file_name in json_name_list:
        json_path = os.path.join(json_dir, file_name)
        with open(json_path, encoding='utf-8') as f:
            json_data = json.load(f)
        structures.append(json_data['structure'])
    with open("./structures/old_structures.json", 'w', encoding='utf-8') as f:
        json.dump(structures, f, indent=4)

    review_structures(structures)

def extract_from_code_block(text):
    matches = re.findall(r'```(.*?)```', text, re.DOTALL)
    if matches:
        return [match.strip() for match in matches]
    else:
        print("No code blocks found")
        return []

def process_item(client, prompt, item, idx):
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': f'```{json.dumps(item)}```'}
        ],
        stream=False,
        temperature=0.0
    )

    result = completion.choices[0].message.content

    json_str = extract_from_code_block(result)[0][len("json\n"):]

    try:
        return json.loads(json_str), idx
    except json.JSONDecodeError as e:
        print(f"decode error: {e}")
        with open("./temp/error.txt", 'w', encoding="utf-8") as f:
            f.write(json_str)
        return reformat_json(json_str)


def review_structures(json_data):
    global client, reshape_prompt
    
    results = []
    

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_item, client, reshape_prompt, item,idx): item for idx, item in enumerate(json_data)}
        
        for future in as_completed(futures):
            try:
                data, idx = future.result()
                if data is not None:
                    results.append((data, idx))
            except Exception as exc:
                print(f'generate error: {exc}')
    
    results.sort(key=lambda x: x[1])
    sorted_results = [item[0] for item in results]

    with open("./structures/new_structures.json", 'w', encoding='utf-8') as f:
        json.dump(sorted_results, f, indent=4)

def rewrite_structures(json_dir, new_structure_path="./structures/new_structures.json"):
    json_file_path_list = [ os.path.join(json_dir, file_name) for file_name in os.listdir(json_dir)]
    with open(new_structure_path, encoding='utf-8') as f:
        new_structure_list = json.load(f)
    for file_path, structure in zip(json_file_path_list, new_structure_list):
        with open(file_path, encoding='utf-8') as f:
            json_data = json.load(f)
        json_data['structure'] = structure
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)



def main():
    parser = argparse.ArgumentParser(description="Process JSON structures.")
    parser.add_argument('command', choices=['review', 'rewrite'], help="Command to execute: 'review' or 'rewrite'.")
    parser.add_argument('json_dir', type=str, help="Directory containing JSON files.")
    
    args = parser.parse_args()

    if args.command == 'review':
        if not os.path.exists(args.json_dir):
            print(f"Error: Directory '{args.json_dir}' does not exist.")
            return
        
        check_json_structures(args.json_dir)

    elif args.command == 'rewrite':
        if not os.path.exists(args.json_dir):
            print(f"Error: Directory '{args.json_dir}' does not exist.")
            return

        rewrite_structures(args.json_dir)
        print("Rewrite completed. JSON files in the directory have been updated.")

if __name__ == "__main__":
    main()