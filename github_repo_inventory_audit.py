#!/usr/bin/env python3

"""
GitHub Repository Inventory Audit

Exports repository metadata for a GitHub organization to CSV.

Collected fields:
- repository name
- archived status
- visibility
- repository URL
- last updated date
- default branch
- branch count

Environment variables:
    GITHUB_TOKEN   GitHub personal access token
    GITHUB_ORG     GitHub organization name

Example:
    python github_repo_inventory_audit.py
"""

import csv
import os
from pathlib import Path
from typing import Any, Dict, List

import requests


GITHUB_API_URL = "https://api.github.com"
OUTPUT_FILE = Path("outputs/repository_inventory.csv")


def get_required_env_var(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it before running the script."
        )

    return value


def create_github_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    return session


def fetch_org_repositories(
    session: requests.Session,
    organization: str,
) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    page = 1

    while True:
        response = session.get(
            f"{GITHUB_API_URL}/orgs/{organization}/repos",
            params={"per_page": 100, "page": page},
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch repositories for org '{organization}'. "
                f"Status: {response.status_code}, Response: {response.text}"
            )

        page_data = response.json()

        if not page_data:
            break

        repos.extend(page_data)
        page += 1

    return repos


def fetch_branch_count(
    session: requests.Session,
    branches_url: str,
) -> int | str:
    url = branches_url.replace("{/branch}", "")

    response = session.get(url, params={"per_page": 100}, timeout=30)

    if response.status_code != 200:
        return "Error"

    return len(response.json())


def export_repositories_to_csv(
    repositories: List[Dict[str, Any]],
    session: requests.Session,
    output_file: Path,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    repositories.sort(key=lambda repo: repo["updated_at"], reverse=True)

    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Repository Name",
                "Archived",
                "Private",
                "URL",
                "Last Updated",
                "Default Branch",
                "Branch Count",
            ]
        )

        for repo in repositories:
            branch_count = fetch_branch_count(session, repo["branches_url"])

            writer.writerow(
                [
                    repo["name"],
                    repo["archived"],
                    repo["private"],
                    repo["html_url"],
                    repo["updated_at"],
                    repo.get("default_branch", "N/A"),
                    branch_count,
                ]
            )


def main() -> None:
    token = get_required_env_var("GITHUB_TOKEN")
    organization = get_required_env_var("GITHUB_ORG")

    session = create_github_session(token)

    repositories = fetch_org_repositories(session, organization)
    export_repositories_to_csv(repositories, session, OUTPUT_FILE)

    print(f"{len(repositories)} repository records written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()