"""Turn GitHub facts + Jev verdicts into a roast.

No LLM writes these lines. Every joke is a template picked at random from
several variants per spice level, and a joke is only used when its underlying
fact actually applies, so each line is tied to a real number or a Jev verdict.

House rules: roast the code and the GitHub habits only. Never looks, real name,
gender, location, age or bio. No profanity.
"""

from __future__ import annotations

import random

SPICE_LEVELS = ("mild", "medium", "spicy")
DEFAULT_SPICE = "medium"
MAX_JOKES = 5

INTROS = {
    "mild": [
        "Alright, let's have a gentle look at {username}'s GitHub.",
        "Pulling up {username}'s public repositories. This will be fine. Probably.",
        "Welcome, {username}. Your code has volunteered for review.",
    ],
    "medium": [
        "So. {username}. Let's talk about what you've been pushing to the internet.",
        "I have read {username}'s entire public GitHub. I would like those minutes back.",
        "Ladies and gentlemen, the public works of {username}. Brace yourselves.",
    ],
    "spicy": [
        "{username}. Your GitHub is a crime scene and I am the forensics team.",
        "I opened {username}'s profile and my linter started crying.",
        "Somebody get a priest. We're going through {username}'s repositories.",
    ],
}

CLOSERS = {
    "mild": [
        "Jev has spoken, kindly. You are... {archetype}. It's a good look on you.",
        "Jev is {confidence}% sure of this: you are {archetype}. Wear it well.",
        "Final verdict from Jev, delivered softly: {archetype}.",
    ],
    "medium": [
        "Jev has spoken. You are... {archetype}.",
        "The math is in, and the math says: {archetype}. {confidence}% confident.",
        "Jev ran the numbers, Jev picked a label, and the label is {archetype}.",
    ],
    "spicy": [
        "Jev has spoken and Jev shows no mercy. You are... {archetype}.",
        "{confidence}% confidence, zero sympathy. You are {archetype}.",
        "Jev looked at everything you've ever pushed and said one word: {archetype}.",
    ],
}


def _pct(value: float) -> int:
    return int(round(value * 100))


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or singular + "s")


def _joke_bank(facts: dict, verdicts: dict) -> list[tuple[bool, dict]]:
    """(applies, variants-per-spice) for every possible joke, in priority order."""
    repos = facts["public_repos"]
    stars = facts["total_stars"]
    stale = facts["stale_repo_count"]
    forks = facts["untouched_forks"]
    night = facts["night_commit_pct"]
    lazy = facts["lazy_commit_count"]
    nodesc = facts["no_description_count"]
    sketchy = facts["suspicious_name_count"]
    followers = facts["followers"]
    following = facts["following"]
    language = facts["top_language"]
    age = facts["account_age_years"]
    sketchy_name = (facts["suspicious_names"] or [""])[0]
    repo_word = _plural(repos, "repo")
    stale_word = _plural(stale, "repo")

    finish = verdicts["finishes_next_project"]["percent"]
    commitment = verdicts["project_commitment"]
    quality = verdicts["commit_message_quality"]
    archetype = verdicts["archetype"]
    ranked = sorted(
        archetype["probabilities"].items(), key=lambda kv: kv[1], reverse=True
    )
    second_name, second_prob = ranked[1] if len(ranked) > 1 else ("", 0.0)
    second_pct = _pct(second_prob)

    bank: list[tuple[bool, dict]] = [
        (
            stars >= 200,
            {
                "mild": [
                    f"{stars} stars across {repos} {repo_word}. Genuinely impressive.",
                    f"{stars} stars. People actually use this stuff. Congratulations.",
                    f"{repos} {repo_word}, {stars} stars. The internet approves.",
                ],
                "medium": [
                    f"{stars} stars. Fine. You win this round. I'll find something else.",
                    f"{stars} stars across {repos} {repo_word}. Impressive numbers for someone who commits like that.",
                    f"{stars} stars. Popularity is not the same as maintenance, and we both know it.",
                ],
                "spicy": [
                    f"{stars} stars. Thousands of people starred this and roughly none of them read the code.",
                    f"{stars} stars across {repos} {repo_word}. Popularity bought you exactly zero discipline.",
                    f"{stars} stars. Congratulations, more people have starred your code than have run it.",
                ],
            },
        ),
        (
            repos > 0 and stars < 200,
            {
                "mild": [
                    f"{repos} public {repo_word} and {stars} stars. Quality over quantity, right?",
                    f"{repos} {repo_word}, {stars} total stars. The stars will come. Someday.",
                    f"{repos} {_plural(repos, 'repository', 'repositories')} out there earning a combined {stars} stars.",
                ],
                "medium": [
                    f"{repos} {repo_word}. {stars} total stars. That's not a portfolio, that's a cry for help.",
                    f"{repos} {_plural(repos, 'repository', 'repositories')} and {stars} stars between them. The math is not flattering.",
                    f"You shipped {repos} {repo_word} and the internet responded with {stars} stars. Deafening.",
                ],
                "spicy": [
                    f"{repos} {repo_word}. {stars} stars. That's not a portfolio, that's a landfill with a README.",
                    f"{stars} stars across {repos} {_plural(repos, 'repository', 'repositories')}. Even your own account is not clicking the button.",
                    f"{repos} public repos, {stars} stars. You are not building software, you are building evidence.",
                ],
            },
        ),
        (
            True,
            {
                "mild": [
                    f"Jev puts your odds of finishing the next side project at {finish}%. Rooting for you.",
                    f"{finish}% chance you finish your next project, says Jev. That's a real chance!",
                    f"Jev, who is very polite, gives you {finish}% on finishing the next one.",
                ],
                "medium": [
                    f"Jev gives you a {finish}% chance of finishing your next project. Jev is being generous.",
                    f"Probability you finish the next side project: {finish}%. Calibrated. Unflattering.",
                    f"Jev ran the numbers on your next project. {finish}%. Start it anyway, I guess.",
                ],
                "spicy": [
                    f"Jev gives you {finish}% odds of finishing your next project, and Jev is rounding up out of pity.",
                    f"{finish}% chance you finish the next one. Your `git init` is a threat to nobody.",
                    f"Jev says {finish}%. That's not a probability, that's a warning label.",
                ],
            },
        ),
        (
            stale > 0,
            {
                "mild": [
                    f"{stale} {stale_word} haven't been pushed to in over a year. They're resting.",
                    f"{stale} {_plural(stale, 'project')} on a long break. Very long. Restful.",
                    f"{stale} {_plural(stale, 'repository', 'repositories')} last saw a commit over a year ago. They miss you.",
                ],
                "medium": [
                    f"{stale} {stale_word} haven't been touched in over a year. They're not projects, they're fossils.",
                    f"{stale} {_plural(stale, 'repository', 'repositories')} {'is' if stale == 1 else 'are'} older than a year since the last push. Archaeology, not engineering.",
                    f"{stale} of your repos have been silent for 365+ days. That's not a codebase, that's a time capsule.",
                ],
                "spicy": [
                    f"{stale} {stale_word} untouched for over a year. That's not a portfolio, that's a cemetery with commit history.",
                    f"{stale} abandoned {_plural(stale, 'repository', 'repositories')}. Somewhere, {stale} {_plural(stale, 'README')} {'is' if stale == 1 else 'are'} still promising 'coming soon'.",
                    f"{stale} {stale_word} haven't been pushed to in a year. Their last commit was a goodbye note and nobody noticed.",
                ],
            },
        ),
        (
            quality["rounded"] <= 3,
            {
                "mild": [
                    f"Jev rates your commit messages {quality['value']} out of 5. Room to grow.",
                    f"Commit message quality: {quality['value']}/5. A few more words wouldn't hurt.",
                    f"{quality['value']} out of 5 on commit messages. 'fix' is doing a lot of heavy lifting.",
                ],
                "medium": [
                    f"Commit message quality: {quality['value']} out of 5. 'fix' is not a sentence.",
                    f"Jev scored your commit messages {quality['value']}/5. Your future self is going to have questions.",
                    f"{quality['value']}/5 for commit messages, with {lazy} of them being pure filler.",
                ],
                "spicy": [
                    f"Commit message quality: {quality['value']} out of 5. 'fix' is not a sentence, it's a shrug with a hash.",
                    f"Jev gave your commit messages {quality['value']}/5. `git log` reads like a ransom note.",
                    f"{quality['value']}/5 on commit messages. {lazy} of them could be replaced by a keyboard falling over.",
                ],
            },
        ),
        (
            quality["rounded"] >= 4,
            {
                "mild": [
                    f"Commit messages score {quality['value']}/5. Genuinely readable. Well done.",
                    f"Jev gave your commit messages {quality['value']} out of 5. No notes.",
                    f"{quality['value']}/5 for commit messages. Somebody has been reading the style guide.",
                ],
                "medium": [
                    f"Commit messages: {quality['value']}/5. Suspiciously good. Who writes these for you?",
                    f"Jev says {quality['value']}/5 on commit messages. Great sentences, shame about the abandoned repos.",
                    f"{quality['value']}/5 commit messages. Beautifully documenting projects nobody is using.",
                ],
                "spicy": [
                    f"Commit messages: {quality['value']}/5. Immaculate prose describing code nobody will ever run.",
                    f"{quality['value']}/5 on commit messages. You write changelogs for ghosts.",
                    f"Jev gave your commit messages {quality['value']}/5. The only 4-star thing here, and it's the text.",
                ],
            },
        ),
        (
            night >= 15,
            {
                "mild": [
                    f"{night}% of your commits land between midnight and 5am. Sleep is also a feature.",
                    f"{night}% of commits after midnight. The night is quiet, I get it.",
                    f"Midnight-to-5am commits: {night}%. Consider a pillow.",
                ],
                "medium": [
                    f"{night}% of your commits happen after midnight. Go to sleep.",
                    f"{night}% of commits land between 00:00 and 05:00. That's not a workflow, that's a symptom.",
                    f"Jev sees {night}% of your commits arriving after midnight. So does your body.",
                ],
                "spicy": [
                    f"{night}% of your commits happen between midnight and 5am. Go to sleep. The bug will still be there.",
                    f"{night}% of commits after midnight. Your best ideas and your worst code arrive in the same hour.",
                    f"{night}% of your commits are nocturnal. You're not a developer, you're a raccoon with push access.",
                ],
            },
        ),
        (
            forks > 0,
            {
                "mild": [
                    f"{forks} {_plural(forks, 'fork')} you never modified. Collecting is a hobby too.",
                    f"{forks} untouched {_plural(forks, 'fork')}. They're for later. Definitely later.",
                    f"You forked {forks} {_plural(forks, 'repo')} and left them exactly as found. Very respectful.",
                ],
                "medium": [
                    f"{forks} {_plural(forks, 'fork')} with zero changes. Forking is not contributing.",
                    f"{forks} {_plural(forks, 'repository', 'repositories')} forked and never touched. That's bookmarking with extra steps.",
                    f"{forks} pristine forks. You clicked a button and called it open source.",
                ],
                "spicy": [
                    f"{forks} {_plural(forks, 'fork')}, zero commits. You're not contributing, you're hoarding other people's work.",
                    f"{forks} untouched forks sitting in your account like trophies you didn't win.",
                    f"{forks} {_plural(forks, 'fork')} you never modified. Somewhere a maintainer felt a chill and didn't know why.",
                ],
            },
        ),
        (
            sketchy > 0,
            {
                "mild": [
                    f"{sketchy} {_plural(sketchy, 'repo')} named things like {sketchy_name!r}. Naming is hard.",
                    f"{sketchy} repo {_plural(sketchy, 'name')} in the 'test / final / v2' family. Classic.",
                    f"Found {sketchy} placeholder-ish repo {_plural(sketchy, 'name')}, starting with {sketchy_name!r}.",
                ],
                "medium": [
                    f"{sketchy} {_plural(sketchy, 'repo')} named like temp files. {sketchy_name!r} was shipped to the production of the soul.",
                    f"{sketchy} {_plural(sketchy, 'repository', 'repositories')} carry names like {sketchy_name!r}. Version control has a rename command.",
                    f"{sketchy} repo {_plural(sketchy, 'name')} {'contains' if sketchy == 1 else 'contain'} 'test', 'final' or 'v2'. None of them were final.",
                ],
                "spicy": [
                    f"{sketchy} {_plural(sketchy, 'repo')} named like unsaved documents. {sketchy_name!r} is not a project, it's a hostage.",
                    f"{sketchy_name!r}. You looked at that name, and you pushed it anyway.",
                    f"{sketchy} {_plural(sketchy, 'repository', 'repositories')} named 'final', 'v2' or 'test'. Nothing was final. Nothing was tested.",
                ],
            },
        ),
        (
            nodesc > 0,
            {
                "mild": [
                    f"{nodesc} {_plural(nodesc, 'repo')} with no description. A sentence would help visitors.",
                    f"{nodesc} {_plural(nodesc, 'repository', 'repositories')} description-free. Mysterious.",
                    f"{nodesc} {_plural(nodesc, 'repo')} skipped the description box. It's right there.",
                ],
                "medium": [
                    f"{nodesc} {_plural(nodesc, 'repo')} with no description. The code is self-documenting, apparently.",
                    f"{nodesc} {_plural(nodesc, 'repository', 'repositories')} with an empty description field. Bold assumption that anyone can guess.",
                    f"{nodesc} {_plural(nodesc, 'repo')} {'tells' if nodesc == 1 else 'tell'} visitors nothing. The README is a rumour.",
                ],
                "spicy": [
                    f"{nodesc} {_plural(nodesc, 'repo')} with no description. You published mystery boxes and called it a portfolio.",
                    f"{nodesc} {_plural(nodesc, 'repository', 'repositories')} {'explains' if nodesc == 1 else 'explain'} nothing. Not to me, not to recruiters, not to you in six months.",
                    f"{nodesc} description-free {_plural(nodesc, 'repo')}. Even you don't remember what they do.",
                ],
            },
        ),
        (
            following > 0 and followers < following,
            {
                "mild": [
                    f"{followers} followers, following {following}. Networking takes time.",
                    f"You follow {following} people and {followers} follow back. Generous of you.",
                    f"{followers}:{following} follower ratio. Community-minded.",
                ],
                "medium": [
                    f"You follow {following} developers. {followers} follow you back. That's not networking, that's fandom.",
                    f"{followers} followers versus {following} following. You're an audience, not an act.",
                    f"Following {following}, followed by {followers}. The internet is not reciprocating.",
                ],
                "spicy": [
                    f"You follow {following} people. {followers} follow you back. You're a fan account with a keyboard.",
                    f"{followers} followers, {following} following. You're subscribing to other people's careers.",
                    f"Following {following}, followed by {followers}. Even the bots scrolled past.",
                ],
            },
        ),
        (
            commitment["rounded"] <= 3,
            {
                "mild": [
                    f"Project commitment: {commitment['value']}/5. Finishing is a skill you can learn.",
                    f"Jev scores your staying power {commitment['value']} out of 5. Not bad, not done.",
                    f"{commitment['value']}/5 on sticking with projects. Momentum is buildable.",
                ],
                "medium": [
                    f"Project commitment: {commitment['value']} out of 5. Starting is not the hard part and you know it.",
                    f"Jev rates your project commitment {commitment['value']}/5, with {_pct(commitment['confidence'])}% confidence.",
                    f"{commitment['value']}/5 for commitment. Your repos have a shorter lifespan than a free trial.",
                ],
                "spicy": [
                    f"Project commitment: {commitment['value']} out of 5. You don't finish projects, you release them into the wild.",
                    f"{commitment['value']}/5 commitment. `git init` is the most optimistic thing you do all year.",
                    f"Jev put your commitment at {commitment['value']}/5. Your side projects have an exit strategy and it's silence.",
                ],
            },
        ),
        (
            bool(language),
            {
                "mild": [
                    f"Mostly {language}. A solid, dependable choice.",
                    f"{language} is clearly home for you. Comfortable.",
                    f"Your top language is {language}. Consistency is nice.",
                ],
                "medium": [
                    f"Top language: {language}. And by 'top' I mean 'only'.",
                    f"Almost everything here is {language}. Comfort zones have IP addresses now.",
                    f"{language}, {language}, and more {language}. The range is inspiring.",
                ],
                "spicy": [
                    f"Top language: {language}. Not a preference, a personality.",
                    f"It's {language} all the way down. Stack Overflow knows you by first name.",
                    f"Everything is {language}. Even your abandoned repos are abandoned in {language}.",
                ],
            },
        ),
        (
            age >= 1,
            {
                "mild": [
                    f"{age} years on GitHub and {repos} public repos. Steady pace.",
                    f"{age} years of account history. Experience counts.",
                    f"On GitHub for {age} years with {stars} stars to show. It's a journey.",
                ],
                "medium": [
                    f"{age} years on GitHub for {repos} {repo_word} and {stars} stars. That's a slow burn.",
                    f"{age} years of account age. The account matured. The commit messages did not.",
                    f"{age} years on GitHub and the highlight reel is {stars} stars. Efficient.",
                ],
                "spicy": [
                    f"{age} years on GitHub, {stars} stars. Time was not the missing ingredient.",
                    f"{age} years of access to unlimited free repositories, and this is the result.",
                    f"{age} years in and your greatest hit has {facts['most_starred_repo_stars']} stars.",
                ],
            },
        ),
        (
            second_prob >= 0.15,
            {
                "mild": [
                    f"Jev also considered {second_name} at {second_pct}%. Close call.",
                    f"Runner-up archetype: {second_name} ({second_pct}%).",
                    f"You were {second_pct}% {second_name} too. Multitalented.",
                ],
                "medium": [
                    f"Jev gave {second_pct}% to {second_name} as well. You contain multitudes, all of them unfinished.",
                    f"Second-place archetype: {second_name} at {second_pct}%. Barely dodged that one.",
                    f"There was a {second_pct}% case for {second_name}. Jev nearly went there.",
                ],
                "spicy": [
                    f"Jev also saw {second_pct}% of {second_name} in you. Two diagnoses, one account.",
                    f"{second_pct}% {second_name} on the side. The probabilities are ganging up on you.",
                    f"Backup verdict: {second_name}, {second_pct}%. There is no good branch here.",
                ],
            },
        ),
    ]
    return bank


def _empty_roast(facts: dict, spice: str, rng: random.Random) -> list[str]:
    username = facts["username"]
    return [
        rng.choice(INTROS[spice]).format(username=username),
        "Zero public repositories. Nothing. An empty stage.",
        rng.choice(
            [
                "I cannot roast code that does not exist, which is its own kind of roast.",
                "This is the cleanest codebase I have ever reviewed, and also the emptiest.",
                "No repos means no bugs. Technically a perfect record.",
            ]
        ),
        f"{facts['account_age_years']} years of account age and not one push. The potential is enormous.",
        "Go build something terrible. Come back. I'll be here.",
    ]


def generate_roast(
    facts: dict, verdicts: dict, spice: str = DEFAULT_SPICE, seed: int | None = None
) -> list[str]:
    """Return 6-7 roast lines: intro, 4-5 fact-anchored jokes, closer."""
    spice = spice if spice in SPICE_LEVELS else DEFAULT_SPICE
    rng = random.Random(seed)
    if facts["public_repos"] == 0:
        return _empty_roast(facts, spice, rng)

    lines = [rng.choice(INTROS[spice]).format(username=facts["username"])]

    applicable = [variants for applies, variants in _joke_bank(facts, verdicts) if applies]
    head, tail = applicable[:3], applicable[3:]
    rng.shuffle(tail)
    chosen = (head + tail)[:MAX_JOKES]
    if len(chosen) < 4:
        chosen = (head + tail)[: max(4, len(applicable))]
    lines.extend(rng.choice(variants[spice]) for variants in chosen)

    archetype = verdicts["archetype"]
    lines.append(
        rng.choice(CLOSERS[spice]).format(
            archetype=archetype["choice"],
            confidence=_pct(archetype["confidence"]),
        )
    )
    return lines
