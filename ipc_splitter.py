import re
import json
import math

def parse_ipc_text(file_path):
    """
    Parses the Indian Penal Code text file to extract sections, titles, and descriptions.

    Args:
        file_path (str): The path to the input text file (data_ipc_law.txt).

    Returns:
        list: A list of dictionaries, where each dictionary represents a section.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return []

    # This regex is the core of the parser. It looks for a pattern that indicates
    # the start of a new section:
    # - ^(\d{1,3}[A-Z]?)\.\s+
    #   - ^ matches the beginning of a line.
    #   - (\d{1,3}[A-Z]?) is a capturing group for the section number.
    #     - \d{1,3} matches 1 to 3 digits (e.g., 1, 52, 120, 302).
    #     - [A-Z]? optionally matches a capital letter (for sections like 52A, 120B).
    #   - \. matches the literal dot after the number.
    #   - \s+ matches one or more whitespace characters.
    # We use re.split to break the text into chunks based on this pattern.
    # The parentheses in the regex cause the delimiter (the section number) to be kept.
    pattern = re.compile(r'^\s*(\d{1,3}[A-Z]?)\.\s+', re.MULTILINE)
    
    # Split the content by the section pattern
    parts = pattern.split(content)
    
    # The first part is the preamble/introductory text, which we can skip.
    # The remaining parts list will look like: ['53', 'Punishments text...', '53A', 'Construction of reference...']
    # We need to iterate through it in pairs.
    sections_data = []
    if len(parts) > 1:
        # We start from index 1 as parts[0] is the text before the first section
        i = 1
        while i < len(parts) - 1:
            section_number = parts[i].strip()
            section_content = parts[i+1].strip()

            # The title is typically the first line of the content.
            content_lines = section_content.split('\n', 1)
            title = content_lines[0].strip()
            
            # The description is the rest of the content.
            description = content_lines[1].strip() if len(content_lines) > 1 else ""

            # Clean up the title by removing trailing characters like '.—'
            title = re.sub(r'[\.—\s]+$', '', title)

            sections_data.append({
                "section": section_number,
                "title": title,
                "description": description
            })
            i += 2
            
    return sections_data

def split_and_save_json(data, num_files=4):
    """
    Splits a list of data into multiple files and saves them as JSON.

    Args:
        data (list): The list of section dictionaries.
        num_files (int): The number of output files to create.
    """
    if not data:
        print("No data to save.")
        return

    total_sections = len(data)
    # Use math.ceil to ensure all items are included, even if division is not even
    chunk_size = math.ceil(total_sections / num_files)
    
    print(f"Total sections found: {total_sections}")
    print(f"Splitting into {num_files} files with approximately {chunk_size} sections each.")

    for i in range(num_files):
        start_index = i * chunk_size
        end_index = start_index + chunk_size
        chunk = data[start_index:end_index]

        output_filename = f'ipc_part_{i+1}.json'
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully created '{output_filename}' with {len(chunk)} sections.")


if __name__ == "__main__":
    ipc_file = 'data_ipc_law.txt'
    parsed_data = parse_ipc_text(ipc_file)
    
    if parsed_data:
        split_and_save_json(parsed_data, num_files=4)
    else:
        print("Parsing failed or the file was empty.")
