const form = document.getElementById("roast-form");
const statusEl = document.getElementById("status");
const results = document.getElementById("results");

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
  const list = document.getElementById("roast-lines");
  list.innerHTML = "";
  data.roast.forEach((line) => {
    const item = document.createElement("li");
    item.textContent = line;
    list.appendChild(item);
  });
  document.getElementById("verdict").textContent = JSON.stringify(data.jev, null, 2);
});
