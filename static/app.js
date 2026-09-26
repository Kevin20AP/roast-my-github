const form = document.getElementById("roast-form");
const input = document.getElementById("username");
const button = document.getElementById("roast-button");
const errorBox = document.getElementById("error");
const loading = document.getElementById("loading");
const loadingText = document.getElementById("loading-text");
const results = document.getElementById("results");
const list = document.getElementById("roast-lines");
const voiceNote = document.getElementById("voice-note");

const LOADING_MESSAGES = [
  "Counting your abandoned repos…",
  "Reading your commit messages. Oh no.",
  "Asking Jev to be gentle. Jev said no.",
  "Calculating the damage…",
  "Consulting the graveyard of side projects…",
];

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let loadingTimer = null;
let audio = null;
let stopKaraoke = null;
let currentRoast = [];

function currentSpice() {
  return document.querySelector('input[name="spice"]:checked').value;
}

/* ---------------- flow ---------------- */

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = input.value.trim().replace(/^@/, "");
  if (!username) return;

  stopEverything();
  errorBox.hidden = true;
  results.hidden = true;
  startLoading();
  button.disabled = true;

  try {
    const response = await fetch("/api/roast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, spice: currentSpice() }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Something broke. Ironic.");
    render(data);
    play(data.roast);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
  } finally {
    stopLoading();
    button.disabled = false;
  }
});

function startLoading() {
  let index = 0;
  loading.hidden = false;
  loadingText.textContent = LOADING_MESSAGES[0];
  loadingTimer = setInterval(() => {
    index = (index + 1) % LOADING_MESSAGES.length;
    loadingText.textContent = LOADING_MESSAGES[index];
  }, 1200);
}

function stopLoading() {
  clearInterval(loadingTimer);
  loading.hidden = true;
}

function stopEverything() {
  if (stopKaraoke) stopKaraoke();
  stopKaraoke = null;
  if (audio) {
    audio.pause();
    audio = null;
  }
  window.speechSynthesis?.cancel();
}

/* ---------------- rendering ---------------- */

function render(data) {
  currentRoast = data.roast;
  results.hidden = false;

  document.getElementById("avatar").src = data.facts.avatar_url || "";
  document.getElementById("avatar").alt = `${data.username}'s avatar`;
  document.getElementById("wanted-name").textContent = `@${data.username}`;

  renderStats(data.facts);
  renderVerdict(data.jev);
  renderTombstone(data.tombstone);
  renderLines(data.roast);
  voiceNote.textContent = "";
  results.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth" });
}

function renderStats(facts) {
  const cards = [
    [facts.public_repos, "public repos"],
    [facts.total_stars, "total stars"],
    [facts.stale_repo_count, "repos untouched 1yr+"],
    [`${facts.night_commit_pct}%`, "commits after midnight"],
    [facts.untouched_forks, "forks never touched"],
    [facts.no_description_count, "repos with no description"],
    [facts.lazy_commit_count, "lazy commit messages"],
    [facts.top_language || "—", "top language"],
    [`${facts.followers}/${facts.following}`, "followers / following"],
    [`${facts.account_age_years}y`, "account age"],
  ];

  const grid = document.getElementById("stats");
  grid.innerHTML = "";
  cards.forEach(([value, label], index) => {
    const card = document.createElement("div");
    card.className = "stat-card";
    card.style.setProperty("--tilt", `${(Math.random() * 8 - 4).toFixed(1)}deg`);
    card.style.transform = `rotate(var(--tilt))`;
    card.style.animationDelay = reducedMotion ? "0s" : `${index * 0.08}s`;
    card.innerHTML = `<span class="stat-value"></span><span class="stat-label"></span>`;
    card.querySelector(".stat-value").textContent = value;
    card.querySelector(".stat-label").textContent = label;
    grid.appendChild(card);
  });
}

function renderVerdict(jev) {
  const pct = jev.finishes_next_project.percent;
  document.getElementById("finish-pct").textContent = pct;
  requestAnimationFrame(() => {
    document.getElementById("gauge-fill").style.width = `${pct}%`;
  });

  flames("commitment-flames", jev.project_commitment);
  document.getElementById("commitment-label").textContent =
    `${jev.project_commitment.value}/5 · Jev confidence ${Math.round(jev.project_commitment.confidence * 100)}%`;

  flames("quality-flames", jev.commit_message_quality);
  document.getElementById("quality-label").textContent =
    `${jev.commit_message_quality.value}/5 · Jev confidence ${Math.round(jev.commit_message_quality.confidence * 100)}%`;

  document.getElementById("archetype-name").textContent = jev.archetype.choice;
  document.getElementById("archetype-desc").textContent = jev.archetype.description;
  document.getElementById("archetype-confidence").textContent =
    Math.round(jev.archetype.confidence * 100);

  const bars = document.getElementById("archetype-bars");
  bars.innerHTML = "";
  Object.entries(jev.archetype.probabilities)
    .sort((a, b) => b[1] - a[1])
    .forEach(([name, probability]) => {
      const row = document.createElement("div");
      row.className = "prob-row";
      row.innerHTML =
        `<div><span class="prob-name"></span><div class="prob-track"><div class="prob-fill"></div></div></div>` +
        `<span class="prob-pct"></span>`;
      row.querySelector(".prob-name").textContent = name;
      row.querySelector(".prob-pct").textContent = `${Math.round(probability * 100)}%`;
      bars.appendChild(row);
      requestAnimationFrame(() => {
        row.querySelector(".prob-fill").style.width = `${Math.round(probability * 100)}%`;
      });
    });
}

function flames(elementId, score) {
  const container = document.getElementById(elementId);
  container.innerHTML = "";
  for (let level = 1; level <= 5; level += 1) {
    const flame = document.createElement("span");
    flame.textContent = "🔥";
    if (level <= score.rounded) flame.classList.add("lit");
    flame.title = score.levels[String(level)] || "";
    container.appendChild(flame);
  }
}

function renderTombstone(tombstone) {
  const area = document.getElementById("tombstone-area");
  if (!tombstone) {
    area.hidden = true;
    return;
  }
  area.hidden = false;
  document.getElementById("tomb-repo").textContent = tombstone.repo;
  document.getElementById("tomb-dates").textContent =
    `Born ${tombstone.born} · Died ${tombstone.died}`;
  document.getElementById("tomb-commits").textContent = tombstone.commits
    ? `Survived by ${tombstone.commits} commits.`
    : "Survived by nobody.";
  document.getElementById("tomb-caption").textContent =
    `Jev picked this one as the most embarrassing or abandoned repo (${Math.round(
      tombstone.confidence * 100
    )}% confidence).`;
}

function renderLines(lines) {
  list.innerHTML = "";
  lines.forEach((line) => {
    const item = document.createElement("li");
    item.textContent = line;
    list.appendChild(item);
  });
}

function highlight(index) {
  [...list.children].forEach((item, i) => {
    item.classList.toggle("active", i === index);
    item.classList.toggle("done", index !== -1 && i < index);
  });
}

/* ---------------- voice + karaoke ---------------- */

/** Each line gets a slice of the audio proportional to its character count. */
function lineSchedule(lines, duration) {
  const total = lines.reduce((sum, line) => sum + line.length, 0) || 1;
  let elapsed = 0;
  return lines.map((line) => {
    const start = elapsed;
    elapsed += (line.length / total) * duration;
    return { start, end: elapsed };
  });
}

function karaoke(lines, duration, currentTime) {
  const schedule = lineSchedule(lines, duration);
  const timer = setInterval(() => {
    const now = currentTime();
    const index = schedule.findIndex((slot) => now >= slot.start && now < slot.end);
    highlight(index === -1 ? lines.length - 1 : index);
  }, 100);
  return () => clearInterval(timer);
}

async function play(lines) {
  stopEverything();
  try {
    const response = await fetch("/api/voice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lines }),
    });
    if (!response.ok) throw new Error("voice unavailable");
    audio = new Audio(URL.createObjectURL(await response.blob()));
    audio.addEventListener("loadedmetadata", () => {
      stopKaraoke = karaoke(lines, audio.duration, () => audio.currentTime);
    });
    audio.addEventListener("ended", finish);
    await audio.play();
    voiceNote.textContent = "Voice by ElevenLabs.";
  } catch (error) {
    voiceNote.textContent = "ElevenLabs is unavailable, so your browser is doing the honours.";
    speak(lines);
  }
}

/** Browser voice so the demo is never silent. */
function speak(lines) {
  if (!window.speechSynthesis) {
    highlight(0);
    return;
  }
  lines.forEach((line, index) => {
    const utterance = new SpeechSynthesisUtterance(line);
    utterance.rate = 1.05;
    utterance.onstart = () => highlight(index);
    if (index === lines.length - 1) utterance.onend = finish;
    window.speechSynthesis.speak(utterance);
  });
}

function finish() {
  if (stopKaraoke) stopKaraoke();
  stopKaraoke = null;
  highlight(-1);
  emojiRain();
}

function emojiRain(count = 34) {
  if (reducedMotion) return;
  for (let i = 0; i < count; i += 1) {
    const drop = document.createElement("span");
    drop.className = "rain-drop";
    drop.textContent = "🔥";
    drop.style.left = `${Math.random() * 100}vw`;
    drop.style.fontSize = `${1.4 + Math.random() * 2}rem`;
    drop.style.animationDuration = `${2 + Math.random() * 2.5}s`;
    drop.style.animationDelay = `${Math.random() * 1.2}s`;
    drop.addEventListener("animationend", () => drop.remove());
    document.body.appendChild(drop);
  }
}

/* ---------------- buttons ---------------- */

document.getElementById("replay").addEventListener("click", () => {
  if (currentRoast.length) play(currentRoast);
});

document.getElementById("again").addEventListener("click", () => {
  stopEverything();
  results.hidden = true;
  input.value = "";
  input.focus();
  window.scrollTo({ top: 0, behavior: reducedMotion ? "auto" : "smooth" });
});

document.getElementById("copy").addEventListener("click", async (event) => {
  await navigator.clipboard.writeText(currentRoast.join("\n"));
  const target = event.currentTarget;
  target.textContent = "✅ Copied!";
  setTimeout(() => {
    target.textContent = "📋 Copy roast";
  }, 1500);
});
