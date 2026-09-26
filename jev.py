"""Jev (TypeSafe System One) judgments about a GitHub user.

Jev does not write text. It returns typed, calibrated judgments: a Choice with a
probability per option, a Noul with the probability a statement is true, and
Scores positioned on described levels. Every question below travels in a single
request so they are evaluated in parallel.
"""

from __future__ import annotations

import os

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

MODEL = "jev-latest"
NO_EMBARRASSING_REPO = "none of these repos are embarrassing"

ARCHETYPES = {
    "The Graveyard Keeper": (
        "Starts many repositories and abandons them after a handful of commits; "
        "most repos have not been pushed to in a long time."
    ),
    "The Tutorial Collector": (
        "Repositories look like course exercises, bootcamp projects, todo apps, "
        "weather apps, or clones of popular products."
    ),
    "The Fork Hoarder": (
        "Forks a lot of other people's repositories and never pushes any commits "
        "to them."
    ),
    "The Midnight Gremlin": (
        "A large share of commits are authored between midnight and 5am."
    ),
    "The Commit Message Poet": (
        "Commit messages are lazy and uninformative: 'fix', 'wip', 'asdf', "
        "'update', 'test', or a single dot."
    ),
    "The Secretly Competent": (
        "Work is consistent, maintained and documented: descriptions on repos, "
        "recent pushes, meaningful commit messages, sustained projects."
    ),
}

COMMITMENT_LEVELS = [
    "Abandons every project within weeks of starting it; nothing is maintained.",
    "Usually loses interest within a couple of months; a rare project survives longer.",
    "Mixed record: some projects are kept alive for a while, many are dropped.",
    "Most projects are maintained for a year or more with steady updates.",
    "Maintains projects for years, with long-running upkeep and documentation.",
]

COMMIT_QUALITY_LEVELS = [
    "Messages are noise: 'asdf', '.', 'fix', 'wip' with no information at all.",
    "Mostly one vague word such as 'update' or 'changes'.",
    "Inconsistent: some messages explain the change, many do not.",
    "Usually clear and specific about what changed.",
    "Consistently descriptive, well-scoped messages that explain what and why.",
]


class JevError(Exception):
    """Jev could not be reached or refused the request."""


def _jev_state(facts: dict) -> dict:
    """The named facts Jev reasons over. Only code habits, never personal data."""
    return {
        "account_age_years": facts["account_age_years"],
        "public_repo_count": facts["public_repos"],
        "own_repo_count": facts["own_repo_count"],
        "forked_repo_count": facts["fork_count"],
        "forks_never_modified": facts["untouched_forks"],
        "total_stars_received": facts["total_stars"],
        "followers": facts["followers"],
        "following": facts["following"],
        "repos_not_pushed_in_over_a_year": facts["stale_repo_count"],
        "repos_with_no_description": facts["no_description_count"],
        "repo_names_that_look_like_throwaways": facts["suspicious_names"],
        "top_language": facts["top_language"],
        "language_spread": facts["language_spread"],
        "commits_analysed": facts["analysed_commits"],
        "percent_of_commits_between_midnight_and_5am": facts["night_commit_pct"],
        "lazy_commit_message_count": facts["lazy_commit_count"],
        "recent_commit_messages": facts["sample_commit_messages"],
        "recent_repositories": facts["recent_repos"],
    }


def _repo_options(facts: dict) -> dict[str, str | None]:
    options: dict[str, str | None] = {}
    for repo in facts["recent_repos"][:10]:
        days = repo.get("days_since_push")
        parts = [repo.get("language") or "no language detected"]
        parts.append(f"{repo.get('stars', 0)} stars")
        parts.append(
            f"last pushed {days} days ago" if days is not None else "never pushed"
        )
        parts.append("a fork" if repo.get("is_fork") else "not a fork")
        parts.append(
            f"described as: {repo['description']}"
            if repo.get("description")
            else "has no description"
        )
        options[repo["name"]] = "; ".join(parts)
    options[NO_EMBARRASSING_REPO] = (
        "None of the listed repositories look embarrassing or abandoned."
    )
    return options


def build_questions(facts: dict) -> dict:
    return {
        "archetype": Choice(
            instructions=(
                "Based on this developer's public GitHub activity, which developer "
                "archetype describes them best?"
            ),
            criteria=dict(ARCHETYPES),
        ),
        "finishes_next_project": Noul(
            instructions=(
                "Will this developer actually finish their next side project?"
            ),
            criteria={
                "true": (
                    "Their track record suggests they will carry the next side "
                    "project through to a finished, maintained state."
                ),
                "false": (
                    "Their track record suggests the next side project will be "
                    "abandoned before it is finished."
                ),
            },
        ),
        "project_commitment": Score(
            instructions=(
                "How committed is this developer to the projects they start, judging "
                "by how long their repositories stay maintained?"
            ),
            criteria=list(COMMITMENT_LEVELS),
        ),
        "commit_message_quality": Score(
            instructions=(
                "How good are this developer's commit messages at describing what "
                "changed?"
            ),
            criteria=list(COMMIT_QUALITY_LEVELS),
        ),
        "most_embarrassing_repo": Choice(
            instructions=(
                "Which of this developer's repository names would a senior engineer "
                "find most embarrassing or most obviously abandoned?"
            ),
            criteria=_repo_options(facts),
        ),
    }


def _score_1_to_5(answer) -> dict:
    """Jev scores are 0-indexed across the levels; the UI shows 1-5."""
    return {
        "value": round(answer.score + 1, 2),
        "rounded": int(round(answer.score)) + 1,
        "confidence": round(answer.confidence, 3),
        "levels": {str(int(k) + 1): v for k, v in answer.legend.items()},
        "probabilities": {
            str(int(k) + 1): round(v, 4) for k, v in answer.probabilities.items()
        },
    }


def judge(facts: dict) -> dict:
    """Ask Jev every question in one request and return plain dicts for the UI."""
    api_key = (os.environ.get("TYPESAFE_API_KEY") or "").strip()
    if not api_key:
        raise JevError("TYPESAFE_API_KEY is not set.")

    try:
        with TypeSafeClient(api_key=api_key) as client:
            response = client.system_one(
                state=_jev_state(facts),
                questions=build_questions(facts),
                model=MODEL,
            )
    except Exception as exc:  # SDK raises a family of TypeSafeError subclasses
        raise JevError(str(exc)) from exc

    archetype = response.choices["archetype"]
    embarrassing = response.choices["most_embarrassing_repo"]
    finishes = response.nouls["finishes_next_project"]

    embarrassing_repo = (
        None if embarrassing.choice == NO_EMBARRASSING_REPO else embarrassing.choice
    )

    return {
        "model": response.model,
        "archetype": {
            "choice": archetype.choice,
            "description": ARCHETYPES.get(archetype.choice, ""),
            "confidence": round(archetype.confidence, 3),
            "probabilities": {
                k: round(v, 4) for k, v in archetype.probabilities.items()
            },
        },
        "finishes_next_project": {
            "probability": round(finishes.noul, 4),
            "percent": round(finishes.noul * 100),
        },
        "project_commitment": _score_1_to_5(response.scores["project_commitment"]),
        "commit_message_quality": _score_1_to_5(
            response.scores["commit_message_quality"]
        ),
        "most_embarrassing_repo": {
            "repo": embarrassing_repo,
            "confidence": round(embarrassing.confidence, 3),
            "probabilities": {
                k: round(v, 4) for k, v in embarrassing.probabilities.items()
            },
        },
    }
