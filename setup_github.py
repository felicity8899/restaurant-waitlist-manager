import os
import sys
import json
import urllib.request
import urllib.error

def make_request(url, token, data=None, method='GET'):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "FastAPI-React-Waitlist-Setup-Agent"
    }
    
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode('utf-8')
        headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode('utf-8'))
        except Exception:
            err_body = e.reason
        return e.code, err_body
    except Exception as e:
        return 500, str(e)

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set.")
        sys.exit(1)
        
    # 1. Get authenticated user
    print("Verifying GitHub token...")
    status, user_info = make_request("https://api.github.com/user", token)
    if status != 200:
        print(f"Failed to authenticate: {user_info}")
        sys.exit(1)
        
    username = user_info["login"]
    print(f"Authenticated as: {username}")
    
    # 2. Check if repo exists, if not create it
    repo_name = "restaurant-waitlist-manager"
    repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
    print(f"Checking if repository {username}/{repo_name} exists...")
    status, repo_info = make_request(repo_url, token)
    
    if status == 200:
        print(f"Repository already exists: {repo_info['html_url']}")
    elif status == 404:
        print(f"Repository does not exist. Creating public repository {repo_name}...")
        create_data = {
            "name": repo_name,
            "description": "A real-time Restaurant Waitlist & Table Manager built with FastAPI, React, and WebSockets.",
            "private": False,
            "has_issues": True
        }
        status, create_info = make_request("https://api.github.com/user/repos", token, data=create_data, method='POST')
        if status not in (200, 201):
            print(f"Failed to create repository: {create_info}")
            sys.exit(1)
        print(f"Successfully created public repository: {create_info['html_url']}")
    else:
        print(f"Unexpected error checking repository: {repo_info}")
        sys.exit(1)
        
    # 3. Parse tasks from _docs/tasks.md
    tasks_file_path = "_docs/tasks.md"
    if not os.path.exists(tasks_file_path):
        print(f"Error: {tasks_file_path} not found.")
        sys.exit(1)
        
    with open(tasks_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    chunks = content.split('\n## ')
    tasks = []
    for chunk in chunks[1:]:
        lines = chunk.split('\n')
        title = lines[0].strip()
        body = '\n'.join(lines[1:]).strip()
        # Clean title if it contains any leading markdown headers from edge cases
        if title.startswith('## '):
            title = title[3:]
        tasks.append({
            "title": title,
            "body": body
        })
        
    print(f"Parsed {len(tasks)} tasks from {tasks_file_path}.")
    
    # 4. Create issues on GitHub
    issues_url = f"https://api.github.com/repos/{username}/{repo_name}/issues"
    print("Creating issues for each task in sequential order...")
    
    # Reverse tasks to create them in sequential order (so task 1 appears last, or keep normal order?)
    # Usually, creating in sequential order is best (Task 1 has lower issue number).
    for idx, task in enumerate(tasks, 1):
        print(f"Creating Issue #{idx}: {task['title']}...")
        issue_data = {
            "title": task["title"],
            "body": task["body"]
        }
        status, issue_info = make_request(issues_url, token, data=issue_data, method='POST')
        if status == 201:
            print(f"  -> Created: {issue_info['html_url']}")
        else:
            print(f"  -> Failed to create issue for task '{task['title']}': {issue_info}")
            
    print("\nAll tasks have been processed!")

if __name__ == "__main__":
    main()
