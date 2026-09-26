const form = document.getElementById("roast-form");
const statusEl = document.getElementById("status");
const results = document.getElementById("results");
const list = document.getElementById("roast-lines");

let audio = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("username").value.trim();
  statusEl.hidden = false;
  statusEl.textContent = "Counting your abandoned repos…";
  results.hidden = true;

  const response = await fetch("/api/roast", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, spice: "medium" }),
  });
  const data = await response.json();

  if (!response.ok) {
    statusEl.textContent = data.error || "Something broke.";
    return;
  }

  statusEl.hidden = true;
  results.hidden = false;
  renderLines(data.roast);
  document.getElementById("verdict").textContent = JSON.stringify(data.jev, null, 2);
  play(data.roast);
});

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
  });
}

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
  const tick = () => {
    const now = currentTime();
    const index = schedule.findIndex((slot) => now >= slot.start && now < slot.end);
    highlight(index === -1 ? lines.length - 1 : index);
  };
  const timer = setInterval(tick, 100);
  return () => clearInterval(timer);
}

async function play(lines) {
  if (audio) {
    audio.pause();
    audio = null;
  }
  window.speechSynthesis?.cancel();

  try {
    const response = await fetch("/api/voice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lines }),
    });
    if (!response.ok) throw new Error("voice unavailable");
    const url = URL.createObjectURL(await response.blob());
    audio = new Audio(url);
    audio.addEventListener("loadedmetadata", () => {
      const stop = karaoke(lines, audio.duration, () => audio.currentTime);
      audio.addEventListener("ended", () => {
        stop();
        highlight(-1);
      });
    });
    await audio.play();
  } catch (error) {
    speak(lines);
  }
}

/** Browser voice so the demo is never silent. */
function speak(lines) {
  if (!window.speechSynthesis) return;
  lines.forEach((line, index) => {
    const utterance = new SpeechSynthesisUtterance(line);
    utterance.rate = 1.05;
    utterance.onstart = () => highlight(index);
    if (index === lines.length - 1) utterance.onend = () => highlight(-1);
    window.speechSynthesis.speak(utterance);
  });
}
