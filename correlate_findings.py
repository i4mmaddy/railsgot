import json
import argparse
import sys
import os

def load_json(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file: {filepath}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Correlate OpenGrep findings with Git changes.")
    parser.add_argument("--git-report", required=True, help="Path to ci_git_report.json")
    parser.add_argument("--opengrep-report", required=True, help="Path to opengrep.json")
    parser.add_argument("--output", default="vulnerability_report.json", help="Output JSON file path")
    
    args = parser.parse_args()
    
    git_data = load_json(args.git_report)
    opengrep_data = load_json(args.opengrep_report)
    
    changed_lines = git_data.get('changed_lines', {})
    git_info = git_data.get('git_info', {})
    ci_context = git_data.get('ci_context', {})
    
    # Extract relevant git details to attach to findings
    commit_details = {
        "commit_hash": git_info.get('commit_hash'),
        "commit_author": git_info.get('commit_author_name'),
        "commit_email": git_info.get('commit_author_email'),
        "commit_message": git_info.get('commit_message'),
        "pr_creator": ci_context.get('pr_creator'),
        "pr_number": ci_context.get('pr_number')
    }
    
    filtered_findings = []
    
    # Handle different OpenGrep/Semgrep JSON formats
    # Usually it's {"results": [...]}
    results = opengrep_data.get('results', [])
    
    print(f"Total OpenGrep findings: {len(results)}")
    
    for finding in results:
        path = finding.get('path')
        start_line = finding.get('start', {}).get('line') or finding.get('start') # Handle different formats if needed
        
        if not path or not start_line:
            continue
            
        # Normalize path (remove leading ./ or /) to match git output
        normalized_path = path.lstrip('./').lstrip('/')
        
        # Check if file was changed
        if normalized_path in changed_lines:
            # Check if line was changed
            if start_line in changed_lines[normalized_path]:
                # Match found!
                enriched_finding = finding.copy()
                enriched_finding['commit_details'] = commit_details
                filtered_findings.append(enriched_finding)
                
    print(f"Findings in changed lines: {len(filtered_findings)}")
    
    report = {
        "summary": {
            "total_findings": len(results),
            "relevant_findings": len(filtered_findings),
            "commit_details": commit_details
        },
        "findings": filtered_findings
    }
    
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=4)
        
    print(f"Report saved to {args.output}")

if __name__ == "__main__":
    main()
