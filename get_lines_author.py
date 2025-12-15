import argparse
import subprocess
import sys
import re
import json

def run_command(cmd, cwd=None):
    """Runs a shell command and returns stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            encoding='utf-8',
            errors='replace'
        )
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return None, str(e)

def parse_blame_output(output):
    """Parses git blame --line-porcelain output."""
    lines_info = []
    current_line = {}
    
    for line in output.splitlines():
        if re.match(r'^[a-f0-9]{40} ', line):
            # Commit hash line, starts a new block
            if current_line:
                lines_info.append(current_line)
            current_line = {'hash': line.split()[0]}
        elif line.startswith('author '):
            current_line['author'] = line[7:]
        elif line.startswith('author-mail '):
            current_line['email'] = line[12:].strip('<>')
        elif line.startswith('author-time '):
            current_line['timestamp'] = line[12:]
        elif line.startswith('summary '):
            current_line['summary'] = line[8:]
        elif line.startswith('\t'):
            # The actual code line
            current_line['code'] = line[1:]
            
    if current_line:
        lines_info.append(current_line)
        
    return lines_info

def get_blame(file_path, start, end, ignore_whitespace=True):
    cmd = ['git', 'blame', '--line-porcelain', '-L', f'{start},{end}', file_path]
    if ignore_whitespace:
        cmd.append('-w')
        
    out, err = run_command(cmd)
    if err and not out:
        print(f"Error running git blame: {err}", file=sys.stderr)
        return None
        
    return parse_blame_output(out)

def get_trace(file_path, start, end):
    """Runs git log -L to show the history of the lines."""
    # git log -L <start>,<end>:<file>
    cmd = ['git', 'log', f'-L{start},{end}:{file_path}']
    out, err = run_command(cmd)
    
    if err and "no match" in err:
         print(f"Error: Could not trace lines. They might not exist in the older history as a block.", file=sys.stderr)
         return None
         
    return out

def analyze_authors(blame_data):
    """Aggregates authors from blame data."""
    authors = {}
    for line in blame_data:
        key = (line.get('author'), line.get('email'))
        if key not in authors:
            authors[key] = 0
        authors[key] += 1
        
    sorted_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)
    return sorted_authors

def find_snippet_in_file(file_path, snippet_text):
    """
    Searches for the snippet text in the file and returns (start_line, end_line).
    Matches exact lines, ignoring leading/trailing whitespace of the snippet block relative to indentation if we were smarter,
    but here we do simple strip-match or exact substring match.
    Let's try exact line sequence match first.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None, None

    # Prepare snippet lines: remove empty start/end lines usually caused by copy-pasting
    snippet_lines = [line for line in snippet_text.splitlines() if line.strip()]
    if not snippet_lines:
        return None, None

    # Simple sliding window search
    # We match stripped content to be robust against indentation changes
    snippet_fingerprint = [l.strip() for l in snippet_lines]
    
    file_fingerprints = [l.strip() for l in file_lines]
    
    n = len(snippet_fingerprint)
    for i in range(len(file_fingerprints) - n + 1):
        window = file_fingerprints[i : i+n]
        if window == snippet_fingerprint:
            # Found match!
            # Return 1-based indices
            return i + 1, i + n
            
    return None, None


def main():
    parser = argparse.ArgumentParser(description="Find the developer responsible for specific lines of code.")
    parser.add_argument("file", help="Path to the file")
    parser.add_argument("--lines", help="Line range (e.g., 10-20) or single line (e.g., 15)", required=False)
    parser.add_argument("--snippet", help="Code snippet string to search for (use quotes)", required=False)
    parser.add_argument("--trace", action="store_true", help="Show full history (git log -L) to verify origin")

    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()
    
    start = end = None
    
    # 0. Snippet Mode
    if args.snippet:
        start, end = find_snippet_in_file(args.file, args.snippet)
        if not start:
            print(f"Error: Snippet not found in {args.file}")
            return
        print(f"Snippet found at lines {start}-{end}")
        args.lines = f"{start}-{end}"

    # Parse lines if not set by snippet
    if not start and args.lines:
        if '-' in args.lines:
            start, end = args.lines.split('-')
        else:
            start = end = args.lines
            
    if not start:
         print("Error: Must provide either --lines or --snippet")
         return

        
    # 1. Run Blame
    blame_data = get_blame(args.file, start, end)
    if not blame_data:
        return

    # 2. Analyze
    authors = analyze_authors(blame_data)
    primary_author = authors[0][0] if authors else ("Unknown", "Unknown")
    
    result = {
        "file": args.file,
        "lines": args.lines,
        "latest_author": {
            "name": primary_author[0],
            "email": primary_author[1],
            "confidence": "High" if len(authors) == 1 else "Medium"
        },
        "all_contributors": [{"name": k[0], "email": k[1], "lines_count": v} for k, v in authors]
    }

    if args.json:
        if args.trace:
            result['trace_output'] = get_trace(args.file, start, end)
        print(json.dumps(result, indent=2))
        return

    print(f"\n--- Blame Analysis for {args.file}:{args.lines} ---")
    print(f"Primary Author (Latest): \033[92m{primary_author[0]} <{primary_author[1]}>\033[0m")
    
    if len(authors) > 1:
        print("\nOther Contributors:")
        for (name, email), count in authors[1:]:
             print(f"  - {name}: {count} lines")

    print("\nSnippet:")
    for item in blame_data[:5]:
        print(f"  {item.get('hash')[:7]} ({item.get('timestamp')}) {item.get('code').strip()}")
    if len(blame_data) > 5:
        print("  ...")

    # 3. Trace Mode
    if args.trace:
        print(f"\n--- History Trace (git log -L {start},{end}:{args.file}) ---")
        print("Review the patches below to find who *originally* introduced the logic, not just formatted it.\n")
        trace_out = get_trace(args.file, start, end)
        if trace_out:
            # Print first 2000 chars to avoid flooding
            print(trace_out[:2000]) 
            if len(trace_out) > 2000:
                print("\n... (Output truncated, use --json for full output) ...")
        else:
            print("No trace history available.")

if __name__ == "__main__":
    main()
