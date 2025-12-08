import subprocess
import json
import os
import re

def run_command(command):
    """Runs a shell command and returns the output."""
    try:
        use_shell = isinstance(command, str)
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=use_shell,
            check=True,
            encoding='utf-8', 
            errors='replace'
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # print(f"Error running command: {e}") 
        # Don't print every error if it's just expected git behavior in some cases, 
        # but here we generally expect success.
        return None

def get_commut_list():
    """Fetches list of all commits with basic metadata."""
    # hash|author|email|date|subject
    cmd = [
        'git', 'log', 
        '--pretty=format:%H|%an|%ae|%ad|%s'
    ]
    output = run_command(cmd)
    commits = []
    if output:
        for line in output.split('\n'):
            parts = line.split('|')
            if len(parts) >= 5:
                commits.append({
                    'hash': parts[0],
                    'author_name': parts[1],
                    'author_email': parts[2],
                    'date': parts[3],
                    'message': "|".join(parts[4:])
                })
    return commits

def parse_diff_for_lines(diff_content):
    """
    Parses a git diff/show output to find changed files and their line numbers.
    Returns a dict: {filename: [line_numbers]}
    """
    file_changes = {}
    current_file = None
    current_lines = []
    
    # Regex for file headers in git show
    # diff --git a/path b/path
    diff_header_pattern = re.compile(r"^diff --git a/(.*) b/(.*)")
    
    # Regex for hunk header
    # @@ -old_start,old_len +new_start,new_len @@
    hunk_header_pattern = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    
    lines = diff_content.split('\n')
    current_new_line_num = 0
    
    for line in lines:
        if line.startswith("diff --git"):
            # New file section starts
            # Save previous
            if current_file:
                file_changes[current_file] = current_lines
            
            match = diff_header_pattern.match(line)
            if match:
                # We use the 'b' path (new path)
                current_file = match.group(2)
            else:
                current_file = None # Should not happen if regex matches
            
            current_lines = []
            current_new_line_num = 0
            continue
            
        if not current_file:
            continue
            
        # Check for hunk header
        hunk_match = hunk_header_pattern.match(line)
        if hunk_match:
            current_new_line_num = int(hunk_match.group(1))
            continue
            
        # Check line content
        if line.startswith('+') and not line.startswith('+++'):
            # Added/Modified line in the new file
            current_lines.append(current_new_line_num)
            current_new_line_num += 1
        elif line.startswith(' '):
            # Context line
            current_new_line_num += 1
        # '-' lines are deletions from old file, don't affect new file line count
        
    # Save last file
    if current_file:
        file_changes[current_file] = current_lines
        
    return file_changes

def get_commit_diff(commit_hash):
    """Gets the full diff for a commit to parse line numbers."""
    cmd = ['git', 'show', '--format=', commit_hash]
    return run_command(cmd)

def main():
    print("Fetching commit list...")
    commits = get_commut_list()
    print(f"Found {len(commits)} commits. Processing details...")
    
    full_history = []
    
    for i, commit in enumerate(commits):
        # Progress indicator
        if i % 10 == 0:
            print(f"Processing commit {i+1}/{len(commits)}...")
            
        diff_output = get_commit_diff(commit['hash'])
        changed_files_map = {}
        if diff_output:
            changed_files_map = parse_diff_for_lines(diff_output)
            
        # Transform map to list of objects as per previous structure
        changed_files_list = []
        for fname, lines in changed_files_map.items():
            changed_files_list.append({
                'file': fname,
                'changed_lines': lines
            })
            
        commit['changed_files'] = changed_files_list
        full_history.append(commit)
        
    output_file = 'git_history.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(full_history, f, indent=4)
        
    print(f"\nFull history saved to {output_file}")

if __name__ == "__main__":
    main()
