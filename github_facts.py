"""Fetch a GitHub user's public data and reduce it to roastable facts."""

from __future__ import annotations

import os
import re
from collections import Counter
from datetime import datetime, timezone

import requests

API = "https://api.github.com"
COMMIT_REPO_LIMIT = 5
COMMITS_PER_REPO = 30
SUSPICIOUS_NAME_RE = re.compile(
    r"(test|final|v2|new|untitled|copy|demo|todo)", re.IGNORECASE
)
LAZY_MESSAGES = {"fix", "wip", "update", "asdf", "test", ".", "final"}


class GitHubError(Exception):
    """A user-facing GitHub problem (missing user, rate limit, outage)."""

    def __init__(self, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "roast-my-github",
        }
    )
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


def _get(session: requests.Session, path: str, **params: object) -> object:
    try:
        response = session.get(f"{API}{path}", params=params, timeout=20)
    except requests.RequestException as exc:
        raise GitHubError(
            "GitHub is not picking up the phone. Even their servers are avoiding "
            "your commit history.",
            503,
        ) from exc

    if response.status_code == 404:
        raise GitHubError(
            "No such user. Either they deleted their account out of shame, or you "
            "made a typo. Both are embarrassing.",
            404,
        )
    if response.status_code in (403, 429) and response.headers.get(
        "X-RateLimit-Remaining"
    ) in ("0", None):
        raise GitHubError(
            "GitHub rate-limited us. Too many people are getting roasted right now. "
            "Grab a coffee ☕ and try again in a minute.",
            429,
        )
    if not response.ok:
        raise GitHubError(
            f"GitHub returned {response.status_code} and no explanation. Relatable.",
            502,
        )
    return response.json()


def _parse(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _days_since(stamp: str | None) -> int | None:
    moment = _parse(stamp)
    if moment is None:
        return None
    return (datetime.now(timezone.utc) - moment).days


def collect_facts(username: str) -> dict:
    """Return a flat, JSON-serializable dict of facts about ``username``."""
    session = _session()
    user = _get(session, f"/users/{username}")
    repos = _get(
        session, f"/users/{username}/repos", per_page=100, sort="pushed", type="owner"
    )
    if not isinstance(repos, list):
        repos = []

    login = user["login"]
    own_repos = [r for r in repos if not r.get("fork")]
    forks = [r for r in repos if r.get("fork")]

    untouched_forks = 0
    for fork in forks:
        created, pushed = _parse(fork.get("created_at")), _parse(fork.get("pushed_at"))
        if created and pushed and (pushed - created).total_seconds() <= 86400:
            untouched_forks += 1

    stale_repos = [
        r for r in own_repos if (_days_since(r.get("pushed_at")) or 0) >= 365
    ]
    suspicious = [r["name"] for r in own_repos if SUSPICIOUS_NAME_RE.search(r["name"])]
    undocumented = [r["name"] for r in own_repos if not (r.get("description") or "").strip()]

    languages = Counter(r["language"] for r in own_repos if r.get("language"))
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)

    commit_repos = own_repos[:COMMIT_REPO_LIMIT]
    commit_messages: list[str] = []
    commits_by_repo: dict[str, int] = {}
    night_commits = 0
    analysed_commits = 0
    for repo in commit_repos:
        try:
            commits = _get(
                session,
                f"/repos/{login}/{repo['name']}/commits",
                per_page=COMMITS_PER_REPO,
            )
        except GitHubError:
            continue  # empty repo, DMCA'd repo, whatever - keep roasting
        if not isinstance(commits, list):
            continue
        commits_by_repo[repo["name"]] = len(commits)
        for commit in commits:
            data = commit.get("commit") or {}
            author = data.get("author") or {}
            account = commit.get("author") or {}
            names = {login.lower(), (user.get("name") or "").lower()}
            if (author.get("name") or "").lower() not in names and (
                account.get("login") or ""
            ).lower() != login.lower():
                continue
            analysed_commits += 1
            message = (data.get("message") or "").splitlines()[0].strip()
            commit_messages.append(message)
            moment = _parse(author.get("date"))
            if moment and moment.hour < 5:
                night_commits += 1

    lazy_commits = sum(
        1
        for m in commit_messages
        if m.strip().lower().rstrip(".!") in LAZY_MESSAGES or len(m.strip()) <= 3
    )
    night_pct = round(100 * night_commits / analysed_commits) if analysed_commits else 0
    lazy_pct = round(100 * lazy_commits / len(commit_messages)) if commit_messages else 0

    account_created = user.get("created_at")
    followers = user.get("followers", 0)
    following = user.get("following", 0)

    most_starred = max(repos, key=lambda r: r.get("stargazers_count", 0), default=None)

    return {
        "username": login,
        "avatar_url": user.get("avatar_url"),
        "profile_url": user.get("html_url"),
        "account_created": account_created,
        "account_age_years": round((_days_since(account_created) or 0) / 365.25, 1),
        "public_repos": user.get("public_repos", 0),
        "own_repo_count": len(own_repos),
        "fork_count": len(forks),
        "untouched_forks": untouched_forks,
        "total_stars": total_stars,
        "followers": followers,
        "following": following,
        "follower_ratio": round(followers / following, 2) if following else None,
        "stale_repo_count": len(stale_repos),
        "stale_repo_names": [r["name"] for r in stale_repos][:10],
        "suspicious_name_count": len(suspicious),
        "suspicious_names": suspicious[:10],
        "no_description_count": len(undocumented),
        "top_language": languages.most_common(1)[0][0] if languages else None,
        "language_spread": dict(languages.most_common(5)),
        "analysed_commits": analysed_commits,
        "night_commit_pct": night_pct,
        "lazy_commit_count": lazy_commits,
        "lazy_commit_pct": lazy_pct,
        "sample_commit_messages": commit_messages[:25],
        "most_starred_repo": (most_starred or {}).get("name"),
        "most_starred_repo_stars": (most_starred or {}).get("stargazers_count", 0),
        "recent_repos": [
            {
                "name": r["name"],
                "description": r.get("description"),
                "language": r.get("language"),
                "stars": r.get("stargazers_count", 0),
                "is_fork": bool(r.get("fork")),
                "created_at": r.get("created_at"),
                "pushed_at": r.get("pushed_at"),
                "days_since_push": _days_since(r.get("pushed_at")),
                "commits_seen": commits_by_repo.get(r["name"]),
            }
            for r in repos[:10]
        ],
    }
