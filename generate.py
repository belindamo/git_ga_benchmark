#!/usr/bin/env python3
"""
GitHub Task Generator - Generates evaluation tasks from GitHub repositories.

This script:
1. Clones the repository to envs/github_qa/<repo_name>
2. Fetches PRs and issues (with comments) to tasks/github_qa/<repo_name>/
3. Uses DSPy with Gemini 2.5 Flash to generate tasks for 5 categories:
   - bug_patterns: Pattern recognition across issues/commits
   - timeline_questions: Timeline understanding and evolution tracking
   - system_interactions: Code component relationships
   - people_process: Expertise mapping from contribution patterns
   - performance_evolution: Optimization attempts and outcomes
4. Deduplicates and saves tasks to tasks/github_qa/<repo_name>.json

Required env vars:
- GOOGLE_API_KEY: For Gemini 2.5 Flash API
- GITHUB_TOKEN (optional): For increased API rate limits

Usage: 
python utils/generate_tasks/github_tasks.py <REPO_URL> [--num-tasks N] [--skip-comments]

Examples:
  # Generate 10 tasks per category (default):
  python utils/generate_tasks/github_tasks.py https://github.com/stanfordnlp/dspy
  
  # Generate 5 tasks per category, skip comments for speed:
  python utils/generate_tasks/github_tasks.py https://github.com/stanfordnlp/dspy --num-tasks 5 --skip-comments
"""

import os
import sys
import json
import subprocess
import requests
import argparse
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
import dspy

# Load environment variables
load_dotenv()

# Configure DSPy with Gemini 2.5 Flash for large context window
lm = dspy.LM(
    "gemini/gemini-2.5-flash", 
    api_key=os.getenv("GOOGLE_API_KEY"), 
    temperature=0.7,
    max_tokens=1000000  # 1M tokens for large context
)
dspy.configure(lm=lm)


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse GitHub URL to extract owner and repo name."""
    # Remove .git suffix if present
    if url.endswith('.git'):
        url = url[:-4]
    
    # Parse URL
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    
    if len(path_parts) >= 2:
        return path_parts[0], path_parts[1]
    else:
        raise ValueError(f"Invalid GitHub URL: {url}")


def clone_repository(repo_url: str, target_dir: Path) -> None:
    """Clone the repository if it doesn't already exist."""
    if target_dir.exists():
        print(f"Repository already exists at {target_dir}")
        return
    
    print(f"Cloning repository to {target_dir}...")
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    
    result = subprocess.run(
        ["git", "clone", repo_url, str(target_dir)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to clone repository: {result.stderr}")
    
    print("Repository cloned successfully")


def fetch_comments(owner: str, repo: str, item_type: str, item_number: int, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Fetch comments for a specific issue or PR."""
    if item_type == "pulls":
        # For PRs, we need both issue comments and review comments
        issue_comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{item_number}/comments"
        review_comments_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{item_number}/comments"
        
        all_comments = []
        
        # Fetch issue-style comments
        response = requests.get(issue_comments_url, headers=headers)
        if response.status_code == 200:
            all_comments.extend(response.json())
        
        # Fetch review comments
        response = requests.get(review_comments_url, headers=headers)
        if response.status_code == 200:
            all_comments.extend(response.json())
            
        return all_comments
    else:
        # For issues, just fetch issue comments
        comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{item_number}/comments"
        response = requests.get(comments_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return []


def fetch_github_data(owner: str, repo: str, data_type: str, save_path: Path, fetch_comments_flag: bool = True) -> List[Dict[str, Any]]:
    """Fetch PRs or issues from GitHub API with comments and save incrementally."""
    print(f"Fetching {data_type} for {owner}/{repo}...")
    
    # Check if we already have data
    if save_path.exists():
        with open(save_path, 'r') as f:
            existing_data = json.load(f)
        print(f"Found existing {data_type} data with {len(existing_data)} items")
        return existing_data
    
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    # GitHub API endpoint
    endpoint = f"https://api.github.com/repos/{owner}/{repo}/{data_type}"
    
    # Add state parameter for issues/PRs
    params = {
        "state": "all",
        "per_page": 100,
        "sort": "created",
        "direction": "desc"
    }
    
    # Add GitHub token if available
    headers = {}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    all_items = []
    page = 1
    
    while True:
        params["page"] = page
        response = requests.get(endpoint, params=params, headers=headers)
        
        if response.status_code != 200:
            print(f"Error fetching {data_type}: {response.status_code} - {response.text}")
            break
        
        items = response.json()
        if not items:
            break
        
        # Fetch comments for each item if requested
        if fetch_comments_flag:
            print(f"  Fetching comments for {len(items)} items...")
            for item in items:
                item_number = item.get('number')
                if item_number:
                    comments = fetch_comments(owner, repo, data_type, item_number, headers)
                    item['comments'] = comments
                    time.sleep(0.1)  # Small delay to be respectful
        
        all_items.extend(items)
        
        # Save incrementally
        with open(save_path, 'w') as f:
            json.dump(all_items, f, indent=2)
        
        print(f"Fetched page {page} ({len(items)} items, total: {len(all_items)})")
        
        # Check if we've hit rate limit
        if 'X-RateLimit-Remaining' in response.headers:
            remaining = int(response.headers['X-RateLimit-Remaining'])
            if remaining < 10:
                print(f"Rate limit low ({remaining} remaining), stopping...")
                break
        
        page += 1
        
        # Small delay to be respectful
        time.sleep(0.5)
    
    print(f"Total {data_type} fetched: {len(all_items)}")
    return all_items


def format_pr_as_xml(pr: Dict[str, Any]) -> str:
    """Format a PR as XML for better structure."""
    comments_xml = ""
    if 'comments' in pr and pr['comments']:
        comments_xml = "\n  <comments>\n"
        for comment in pr['comments'][:10]:  # Limit to 10 comments
            comments_xml += f"""    <comment>
      <author>{comment.get('user', {}).get('login', 'unknown')}</author>
      <created_at>{comment.get('created_at', 'unknown')}</created_at>
      <body>{comment.get('body', 'No content')[:500]}</body>
    </comment>\n"""
        comments_xml += "  </comments>"
    
    return f"""<pull_request number="{pr.get('number', 'N/A')}">
  <title>{pr.get('title', 'No title')}</title>
  <state>{pr.get('state', 'unknown')}</state>
  <author>{pr.get('user', {}).get('login', 'unknown')}</author>
  <created_at>{pr.get('created_at', 'unknown')}</created_at>
  <updated_at>{pr.get('updated_at', 'unknown')}</updated_at>
  <merged>{pr.get('merged', False)}</merged>
  <body>{pr.get('body', 'No description')}</body>{comments_xml}
</pull_request>"""


def format_issue_as_xml(issue: Dict[str, Any]) -> str:
    """Format an issue as XML for better structure."""
    # Skip if it's a PR (PRs also appear as issues in GitHub API)
    if 'pull_request' in issue:
        return ""
    
    comments_xml = ""
    if 'comments' in issue and issue['comments']:
        comments_xml = "\n  <comments>\n"
        for comment in issue['comments'][:10]:  # Limit to 10 comments
            comments_xml += f"""    <comment>
      <author>{comment.get('user', {}).get('login', 'unknown')}</author>
      <created_at>{comment.get('created_at', 'unknown')}</created_at>
      <body>{comment.get('body', 'No content')[:500]}</body>
    </comment>\n"""
        comments_xml += "  </comments>"
    
    return f"""<issue number="{issue.get('number', 'N/A')}">
  <title>{issue.get('title', 'No title')}</title>
  <state>{issue.get('state', 'unknown')}</state>
  <author>{issue.get('user', {}).get('login', 'unknown')}</author>
  <created_at>{issue.get('created_at', 'unknown')}</created_at>
  <updated_at>{issue.get('updated_at', 'unknown')}</updated_at>
  <labels>{', '.join([label['name'] for label in issue.get('labels', [])])}</labels>
  <body>{issue.get('body', 'No description')}</body>{comments_xml}
</issue>"""


# DSPy Signatures for task generation
class GitHubQATask(dspy.Signature):
    """A single GitHub QA task."""
    task_id: str = dspy.InputField()
    task: str = dspy.InputField()
    success_criteria: str = dspy.InputField()


class GenerateGitHubQATasks(dspy.Signature):
    """Generate multiple GitHub QA tasks based on repository data at once.
    
    IMPORTANT: While we use GitHub PRs and issues to generate tasks, the agent solving these tasks will ONLY have access to:
    - The cloned git repository 
    - Git history and commit messages
    - File contents and directory structure
    
    The agent will NOT have access to:
    - PR numbers or PR metadata
    - Issue numbers or issue metadata
    - GitHub comments, reviews, or any GitHub-specific features
    
    Although success criteria references information available in a git repository, do NOT include explicit git commits, branches, or tags in the success criteria. 
    """
    
    task_type: str = dspy.InputField(desc="The type of task to generate (bug_patterns, timeline_questions, system_interactions, people_process, performance_evolution)")
    task_type_description: str = dspy.InputField(desc="Description of what this task type should test")
    pull_requests: str = dspy.InputField(desc="XML-formatted pull requests from the repository (for context to generate tasks)")
    issues: str = dspy.InputField(desc="XML-formatted issues from the repository (for context to generate tasks)")
    examples: str = dspy.InputField(desc="Example tasks to model after")
    repo_name: str = dspy.InputField(desc="Name of the repository")
    num_tasks: int = dspy.InputField(desc="Number of tasks to generate")
    
    tasks: List[GitHubQATask] = dspy.OutputField(desc="List of generated tasks with unique IDs, questions, and success criteria")
    reasoning: str = dspy.OutputField(desc="Brief explanation of the generated tasks and their diversity")


class DeduplicateTasks(dspy.Signature):
    """Remove duplicate or highly similar tasks from a list."""
    
    tasks: List[GitHubQATask] = dspy.InputField(desc="List of tasks to deduplicate")
    
    unique_tasks: List[GitHubQATask] = dspy.OutputField(desc="List of unique tasks after removing duplicates")
    removed_count: int = dspy.OutputField(desc="Number of duplicate tasks removed")


def generate_tasks_for_type(
    task_type: str,
    task_description: str,
    prs: List[Dict[str, Any]],
    issues: List[Dict[str, Any]], 
    examples: List[Dict[str, Any]],
    repo_name: str,
    num_tasks: int = 10
) -> List[Dict[str, Any]]:
    """Generate tasks for a specific task type."""
    print(f"\n=== Generating {num_tasks} tasks for {task_type} ===")
    
    # Format PRs and issues as XML
    pr_xml = "\n".join([format_pr_as_xml(pr) for pr in prs[:30]])  # Limit to 30 most recent
    issue_xml = "\n".join([xml for xml in [format_issue_as_xml(issue) for issue in issues[:30]] if xml])
    
    # Format examples with updated context
    examples_text = """IMPORTANT: Success criteria should be attainable via referencing information available in a git repository:
- Commit hashes, commit messages, commit authors, commit dates
- File changes, file paths, code modifications
- Branch names, tags, merge commits
- Git log output, git blame information

Do NOT reference:
- PR numbers or PR titles
- Issue numbers or issue descriptions
- GitHub comments or reviews

Do NOT include explicit git commits, branches, or tags in the success criteria. 

Examples:
"""
    examples_text += "\n".join([
        f"Example {i+1}:\n- Task ID: {ex['task_id']}\n- Task: {ex['task']}"
        for i, ex in enumerate(examples)
    ])
    
    # Generate all tasks at once
    generator = dspy.ChainOfThought(GenerateGitHubQATasks)
    deduplicator = dspy.ChainOfThought(DeduplicateTasks)
    
    try:
        print(f"  Generating batch of {num_tasks} tasks...")
        result = generator(
            task_type=task_type,
            task_type_description=task_description,
            pull_requests=pr_xml,
            issues=issue_xml,
            examples=examples_text,
            repo_name=repo_name,
            num_tasks=num_tasks
        )
        
        print(f"  Generated {len(result.tasks)} tasks, deduplicating...")
        
        # Deduplicate
        dedup_result = deduplicator(tasks=result.tasks)
        
        print(f"  Removed {dedup_result.removed_count} duplicates, {len(dedup_result.unique_tasks)} unique tasks remain")
        
        # Convert to output format
        generated_tasks = []
        for task in dedup_result.unique_tasks:
            generated_tasks.append({
                "task_id": task.task_id,
                "task": task.task,
                "success_criteria": task.success_criteria,
                "dir_name": f"github_qa/{repo_name}"
            })
        
        return generated_tasks
        
    except Exception as e:
        print(f"  ✗ Error generating tasks: {str(e)}")
        return []


def main():
    """
    Main entry point for generating GitHub QA evaluation tasks.
    
    Processes a GitHub repository to generate evaluation tasks by:
    - Cloning the repo and fetching PR/issue data
    - Generating tasks across 5 categories using DSPy/Gemini
    - Deduplicating and saving tasks for agent evaluation
    
    Output structure:
    - Repository: envs/github_qa/<repo_name>/
    - PR/Issue data: tasks/github_qa/<repo_name>/{pr,issue}.json
    - Generated tasks: tasks/github_qa/<repo_name>.json
    """
    parser = argparse.ArgumentParser(description="Generate GitHub QA tasks from a repository")
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("--num-tasks", type=int, default=10, help="Number of tasks to generate per type (default: 10)")
    parser.add_argument("--skip-comments", action="store_true", help="Skip fetching comments to speed up the process")
    args = parser.parse_args()
    
    # Check authentication status
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        print("✅ GitHub authentication configured")
        # Quick rate limit check
        headers = {"Authorization": f"token {github_token}"}
        rate_response = requests.get("https://api.github.com/rate_limit", headers=headers)
        if rate_response.status_code == 200:
            remaining = rate_response.json()['rate']['remaining']
            limit = rate_response.json()['rate']['limit']
            print(f"   Rate limit: {remaining}/{limit} requests remaining")
    else:
        print("⚠️  No GitHub authentication found - using anonymous access (60 requests/hour)")
        print("   See utils/generate_tasks/github_auth_setup.md for authentication setup")
        print()
    
    # Parse repository URL
    owner, repo_name = parse_github_url(args.repo_url)
    print(f"Processing repository: {owner}/{repo_name}")
    
    # Define paths
    env_dir = Path("envs/github_qa") / repo_name
    task_dir = Path("tasks/github_qa") / repo_name
    pr_path = task_dir / "pr.json"
    issue_path = task_dir / "issue.json"
    output_path = Path("tasks/github_qa") / f"{repo_name}.json"
    
    # Step 1: Clone repository
    clone_repository(args.repo_url, env_dir)
    
    # Step 2: Fetch PRs with comments
    prs = fetch_github_data(owner, repo_name, "pulls", pr_path, fetch_comments_flag=not args.skip_comments)
    
    # Step 3: Fetch Issues with comments
    issues = fetch_github_data(owner, repo_name, "issues", issue_path, fetch_comments_flag=not args.skip_comments)
    
    # Step 4: Load examples
    examples_path = Path("tasks/github_qa/dspy.json")
    with open(examples_path, 'r') as f:
        examples = json.load(f)
    
    # Task type definitions from README
    task_types = {
        "bug_patterns": "Tests pattern recognition across multiple issues and commits. Agents must identify recurring problems, root causes, and solutions by analyzing commit history and issue patterns.",
        "timeline_questions": "Tests timeline understanding and evolution tracking. Agents must trace how features developed over time, including challenges, phases, and implementation details from git history.",
        "system_interactions": "Tests understanding of how different code components affect each other. Agents must explain design rationale and system architecture decisions by analyzing code relationships.",
        "people_process": "Tests expertise mapping from contribution patterns. Agents must identify the right people for tasks based on actual commit patterns and areas of expertise.",
        "performance_evolution": "Tests understanding of optimization attempts and outcomes. Agents must track what approaches were tried, what worked, what failed, and why."
    }
    
    # Step 5: Generate tasks for each type
    all_tasks = []
    
    for task_type, description in task_types.items():
        # Filter examples for this task type
        type_examples = [ex for ex in examples if task_type in ex['task_id']]
        
        tasks = generate_tasks_for_type(
            task_type=task_type,
            task_description=description,
            prs=prs,
            issues=issues,
            examples=type_examples if type_examples else examples,  # Use all examples if no specific ones
            repo_name=repo_name,
            num_tasks=args.num_tasks
        )
        
        all_tasks.extend(tasks)
    
    # Step 6: Save all tasks
    print(f"\nSaving {len(all_tasks)} tasks to {output_path}")
    with open(output_path, 'w') as f:
        json.dump(all_tasks, f, indent=2)
    
    print("\n✅ Task generation complete!")
    print(f"- Repository cloned to: {env_dir}")
    print(f"- PRs saved to: {pr_path} (with comments: {not args.skip_comments})")
    print(f"- Issues saved to: {issue_path} (with comments: {not args.skip_comments})")
    print(f"- Tasks saved to: {output_path}")
    print(f"- Total tasks generated: {len(all_tasks)}")


if __name__ == "__main__":
    main()
