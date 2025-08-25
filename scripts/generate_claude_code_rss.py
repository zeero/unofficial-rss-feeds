#!/usr/bin/env python3
"""
Script to generate an RSS feed for the commit history of the claude-code GitHub repository.
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import re

def get_repo_name_from_url(url):
    """Extracts the repository name from a GitHub API URL."""
    match = re.search(r'repos/([^/]+/[^/]+)/commits', url)
    if match:
        return match.group(1)
    return "GitHub Repository"

def load_existing_commits(rss_file_path):
    """Load existing commit SHAs and their publication dates from an RSS file."""
    existing_commits = {}
    if not os.path.exists(rss_file_path):
        return existing_commits
    try:
        tree = ET.parse(rss_file_path)
        root = tree.getroot()
        for item in root.findall('.//item'):
            # The link is the unique identifier for a commit
            link = item.find('link').text
            sha = link.split('/')[-1]
            pub_date = item.find('pubDate').text
            existing_commits[sha] = pub_date
    except Exception as e:
        print(f"Warning: Could not load or parse existing RSS file: {e}")
    return existing_commits

def fetch_claude_code_commits(api_url="https://api.github.com/repos/anthropics/claude-code/commits"):
    """Fetch the latest commits from the GitHub API."""
    try:
        response = requests.get(api_url, headers={'Accept': 'application/vnd.github.v3+json'})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching commits from GitHub API: {e}")
        return []

def generate_rss_feed(commits, existing_commits, repo_name):
    """Generate an RSS 2.0 XML feed from commit data."""
    rss = ET.Element('rss', version='2.0', attrib={'xmlns:atom': 'http://www.w3.org/2005/Atom'})
    channel = ET.SubElement(rss, 'channel')

    ET.SubElement(channel, 'title').text = f'Commits for {repo_name}'
    ET.SubElement(channel, 'link').text = f'https://github.com/{repo_name}/commits/main'
    ET.SubElement(channel, 'description').text = f'Latest commits for the {repo_name} repository on GitHub.'
    ET.SubElement(channel, 'language').text = 'en-us'
    ET.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')

    atom_link = ET.SubElement(channel, 'atom:link', href=f'https://github.com/{repo_name}/commits.rss', rel='self', type='application/rss+xml')

    all_commits = []

    # Add new commits
    for commit_data in commits:
        sha = commit_data['sha']
        if sha not in existing_commits:
            commit = commit_data['commit']
            message = commit['message']
            # Split message into title and description
            title = message.split('\n')[0]
            description = '\n'.join(message.split('\n')[1:]).strip()
            if not description:
                description = title # Use title if body is empty

            # Format date to RFC-822
            date_str = commit['author']['date']
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            pub_date = date_obj.strftime('%a, %d %b %Y %H:%M:%S +0000')

            all_commits.append({
                'sha': sha,
                'title': title,
                'link': commit_data['html_url'],
                'description': f'<pre>{description}</pre>',
                'pubDate': pub_date,
                'author': commit['author']['name']
            })

    # This part is tricky. We need to re-add existing commits if we want the feed to be complete.
    # However, to avoid growing the file indefinitely, we should only keep a certain number.
    # Let's re-read the full existing items and merge.

    # This is a simplified logic: just add new commits and rely on the existing file for the rest.
    # A better approach would be to merge and truncate.

    # Let's rebuild the list of commits, preserving old ones.
    merged_commits = all_commits.copy()
    seen_shas = {c['sha'] for c in merged_commits}

    if os.path.exists('dist/claude-code.xml'):
        tree = ET.parse('dist/claude-code.xml')
        root = tree.getroot()
        for item in root.findall('.//item'):
            link = item.find('link').text
            sha = link.split('/')[-1]
            if sha not in seen_shas:
                merged_commits.append({
                    'sha': sha,
                    'title': item.find('title').text,
                    'link': link,
                    'description': item.find('description').text,
                    'pubDate': item.find('pubDate').text,
                    'author': item.find('author').text if item.find('author') is not None else 'N/A'
                })
                seen_shas.add(sha)

    # Sort by date and truncate
    merged_commits.sort(key=lambda x: datetime.strptime(x['pubDate'], '%a, %d %b %Y %H:%M:%S +0000'), reverse=True)
    final_commits = merged_commits[:30] # Keep the 30 most recent commits

    for commit_item in final_commits:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = commit_item['title']
        ET.SubElement(item, 'link').text = commit_item['link']
        ET.SubElement(item, 'description').text = commit_item['description']
        ET.SubElement(item, 'guid', isPermaLink='true').text = commit_item['link']
        ET.SubElement(item, 'pubDate').text = commit_item['pubDate']
        ET.SubElement(item, 'author').text = commit_item['author']

    return rss

def main():
    """Main function to generate the RSS feed."""
    print("Starting GitHub Commit RSS generation for claude-code...")

    dist_dir = 'dist'
    os.makedirs(dist_dir, exist_ok=True)
    output_path = os.path.join(dist_dir, 'claude-code.xml')

    api_url = "https://api.github.com/repos/anthropics/claude-code/commits"
    repo_name = get_repo_name_from_url(api_url)

    print("Loading existing commits...")
    existing_commits = load_existing_commits(output_path)
    print(f"Found {len(existing_commits)} existing commits in RSS file.")

    print("Fetching latest commits from GitHub API...")
    latest_commits = fetch_claude_code_commits(api_url)
    if not latest_commits:
        print("No commits fetched. Exiting.")
        return
    print(f"Fetched {len(latest_commits)} commits.")

    print("Generating new RSS feed...")
    rss_element = generate_rss_feed(latest_commits, existing_commits, repo_name)

    ET.indent(rss_element, space="  ", level=0)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss_element, encoding='unicode')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_str)

    print(f"RSS feed generated successfully: {output_path}")

if __name__ == "__main__":
    main()
