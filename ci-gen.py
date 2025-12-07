import os
import json
import subprocess
import sys

def run_command(command):
    """Runs a shell command and returns the output."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # If git command fails (e.g. not a git repo), return None or empty
        return None

def get_git_info():
    """Fetches basic git information using git commands."""
    info = {}
    
    # Commit Hash
    info['commit_hash'] = run_command("git rev-parse HEAD")
    
    # Commit Author (Name and Email)
    info['commit_author_name'] = run_command("git log -1 --pretty=format:'%an'")
    info['commit_author_email'] = run_command("git log -1 --pretty=format:'%ae'")
    
    # Commit Message
    info['commit_message'] = run_command("git log -1 --pretty=format:'%s'")
    
    return info

def get_changed_files():
    """Fetches list of changed files between HEAD and previous commit."""
    # For a push event, we often want changes in the latest commit or range.
    # In CI, sometimes checkout is shallow. Assuming fetch-depth: 0 or sufficient depth.
    
    # Get list of changed files in the last commit
    files_output = run_command("git diff-tree --no-commit-id --name-only -r HEAD")
    if files_output:
        return files_output.split('\n')
    return []

def get_file_diff(filepath):
    """Gets the diff for a specific file."""
    return run_command(f"git diff HEAD~1 HEAD -- {filepath}")

def get_github_actions_context():
    """Parses GitHub Actions environment variables and event payload."""
    context = {}
    
    # Basic Env Vars
    context['actor'] = os.getenv('GITHUB_ACTOR') # User who triggered the workflow
    context['event_name'] = os.getenv('GITHUB_EVENT_NAME')
    context['repository'] = os.getenv('GITHUB_REPOSITORY')
    context['ref'] = os.getenv('GITHUB_REF')
    
    # Event Payload (JSON)
    event_path = os.getenv('GITHUB_EVENT_PATH')
    if event_path and os.path.exists(event_path):
        try:
            with open(event_path, 'r') as f:
                payload = json.load(f)
                
            context['event_payload'] = payload
            
            # Extract PR Creator if it's a PR event
            if context['event_name'] == 'pull_request':
                context['pr_creator'] = payload.get('pull_request', {}).get('user', {}).get('login')
                context['pr_title'] = payload.get('pull_request', {}).get('title')
                context['pr_number'] = payload.get('pull_request', {}).get('number')
            
            # For push events, the pusher is usually the actor
            if context['event_name'] == 'push':
                context['pusher'] = payload.get('pusher', {}).get('name')
                
        except Exception as e:
            context['error_parsing_event'] = str(e)
            
    return context

def main():
    print("Gathering CI/CD and Git Details...")
    
    data = {
        'git_info': get_git_info(),
        'ci_context': get_github_actions_context(),
        'changes': []
    }
    
    # Get changed files and their diffs
    changed_files = get_changed_files()
    data['changed_files_list'] = changed_files
    
    for file in changed_files:
        # Skip binary files or deleted files if needed, but for now capture all text diffs
        diff = get_file_diff(file)
        if diff:
            data['changes'].append({
                'file': file,
                'diff': diff
            })
            
    # Output as JSON
    print(json.dumps(data, indent=4))
    
    # Also write to a file for easy consumption by other steps
    with open('ci_git_report.json', 'w') as f:
        json.dump(data, f, indent=4)
        
    print("\nReport saved to ci_git_report.json")

if __name__ == "__main__":
    main()
