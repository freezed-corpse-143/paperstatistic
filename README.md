# NLP Processing Pipeline

This repository contains a set of Python scripts designed to process and analyze JSON files containing structured text data. The scripts are part of an NLP pipeline that checks and rewrites JSON structures, performs word frequency analysis, refines logical flows, and extracts experiment and task/technique-related information.

## Scripts Overview

### 1. `structures_check.py`
- **Purpose**: Reviews and rewrites the structure of JSON files to ensure they conform to a predefined set of top-level nodes.
- **Usage**:
  - To review structures:
    ```bash
    python structures_check.py review <json_dir>
    ```
  - To rewrite structures:
    ```bash
    python structures_check.py rewrite <json_dir>
    ```
- **Output**: Saves reviewed structures to `./structures/old_structures.json` and rewritten structures to `./structures/new_structures.json`.

### 2. `words_analysis.py`
- **Purpose**: Performs word frequency analysis on the text data within JSON files, filtering out stop words and current words.
- **Usage**:
  ```bash
  python words_analysis.py <dir_path> [--stop_words_path <stop_words_path>] [--current_words_path <current_words_path>]
  ```
- **Output**: Saves new words to `./new_words.txt` and prints word statistics.

### 3. `logical_flow_refine.py`
- **Purpose**: Generates and refines logical flow frameworks from the text in JSON files, focusing on compositional patterns.
- **Usage**:
  ```bash
  python logical_flow_refine.py <json_dir>
  ```
- **Output**: Saves logical flow frameworks to `./logical_flow/` directory, with separate JSON files for each section (e.g., `abstract.json`, `introduction.json`).

### 4. `extract_experiment.py`
- **Purpose**: Extracts experiment-related information such as experiment types, baselines, benchmarks, and metrics from JSON files.
- **Usage**:
  ```bash
  python extract_experiment.py <json_dir>
  ```
- **Output**: Saves extracted experiment information to `./extract_infomation/experiment.json`.

### 5. `extract_task_technique.py`
- **Purpose**: Extracts task and technique-related information such as task names, descriptions, challenges, and techniques from JSON files.
- **Usage**:
  ```bash
  python extract_task_technique.py <json_dir>
  ```
- **Output**: Saves extracted task and technique information to `./extract_infomation/task.json` and `./extract_infomation/technique.json`.

## Setup

1. **Environment Variables**:
   - Ensure the `BAILIAN_API_KEY` environment variable is set with the appropriate API key for the OpenAI client.

2. **Dependencies**:
   - Install the required Python packages:
     ```bash
     pip install openai
     ```

3. **Directory Structure**:
   - Ensure the input JSON files are placed in the specified directory (`<json_dir>` or `<dir_path>`).
   - The scripts will create necessary output directories (`./structures`, `./logical_flow`, `./extract_infomation`) automatically.

## Example Usage

To process a directory of JSON files and check/rewrite their structures:

```bash
python structures_check.py review ./data/json_files
python structures_check.py rewrite ./data/json_files
```

To analyze word frequencies in a directory of JSON files:

```bash
python words_analysis.py ./data/json_files --stop_words_path ./stop_words.txt --current_words_path ./current_words.txt
```

To generate logical flow frameworks from JSON files:

```bash
python logical_flow_refine.py ./data/json_files
```

To extract experiment information from JSON files:

```bash
python extract_experiment.py ./data/json_files
```

To extract task and technique information from JSON files:

```bash
python extract_task_technique.py ./data/json_files
```

## Notes

- The scripts use the OpenAI API for certain tasks, such as reformatting JSON and generating logical flows. Ensure you have the necessary API key and access.
- The scripts are designed to handle large datasets efficiently using multi-threading where applicable.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.