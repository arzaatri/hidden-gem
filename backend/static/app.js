const searchInput = document.getElementById("search-input");
const suggestionsList = document.getElementById("suggestions");
const selectedList = document.getElementById("selected-games");
const mineButton = document.getElementById("mine-button");
const resultsSection = document.getElementById("results");

let maxSelectedGames = 5;
let selectedGames = [];
let searchDebounceTimer = null;

async function loadConfig() {
  const response = await fetch("/api/config");
  const config = await response.json();
  maxSelectedGames = config.max_selected_games;
}

async function searchGames(query) {
  const response = await fetch(`/api/games/search?q=${encodeURIComponent(query)}`);
  return response.json();
}

function renderSuggestions(games) {
  suggestionsList.innerHTML = "";
  const selectedIds = new Set(selectedGames.map((g) => g.game_id));
  const unselected = games.filter((g) => !selectedIds.has(g.game_id));

  if (unselected.length === 0) {
    suggestionsList.classList.add("hidden");
    return;
  }

  for (const game of unselected) {
    const item = document.createElement("li");
    item.textContent = game.name;
    item.addEventListener("click", () => selectGame(game));
    suggestionsList.appendChild(item);
  }
  suggestionsList.classList.remove("hidden");
}

function selectGame(game) {
  if (selectedGames.length >= maxSelectedGames) return;
  selectedGames.push(game);
  searchInput.value = "";
  suggestionsList.classList.add("hidden");
  renderSelectedGames();
}

function deselectGame(gameId) {
  selectedGames = selectedGames.filter((g) => g.game_id !== gameId);
  renderSelectedGames();
}

function renderSelectedGames() {
  selectedList.innerHTML = "";
  for (const game of selectedGames) {
    const chip = document.createElement("li");
    chip.className = "chip";
    chip.innerHTML = `<span>${game.name}</span>`;
    const removeButton = document.createElement("button");
    removeButton.textContent = "×";
    removeButton.addEventListener("click", () => deselectGame(game.game_id));
    chip.appendChild(removeButton);
    selectedList.appendChild(chip);
  }

  const atMax = selectedGames.length >= maxSelectedGames;
  searchInput.disabled = atMax;
  searchInput.placeholder = atMax
    ? `You've picked ${maxSelectedGames} games`
    : "Search for a game...";
  mineButton.disabled = selectedGames.length === 0;
}

function renderResults(games) {
  resultsSection.innerHTML = "";
  if (games.length === 0) {
    resultsSection.innerHTML = "<p>No hidden gems found for that selection.</p>";
    return;
  }
  for (const game of games) {
    const card = document.createElement("article");
    card.className = "game-card";
    card.innerHTML = `
      <h3>${game.name}</h3>
      <div class="genres">${game.genres.join(", ")}</div>
      <p>${game.summary ?? ""}</p>
    `;
    resultsSection.appendChild(card);
  }
}

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounceTimer);
  const query = searchInput.value.trim();
  if (query.length === 0) {
    suggestionsList.classList.add("hidden");
    return;
  }
  searchDebounceTimer = setTimeout(async () => {
    const games = await searchGames(query);
    renderSuggestions(games);
  }, 200);
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".search-box")) {
    suggestionsList.classList.add("hidden");
  }
});

mineButton.addEventListener("click", async () => {
  resultsSection.innerHTML = "<p>Mining...</p>";
  const response = await fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ game_ids: selectedGames.map((g) => g.game_id) }),
  });
  if (!response.ok) {
    const error = await response.json();
    resultsSection.innerHTML = `<p class="error">${error.detail}</p>`;
    return;
  }
  renderResults(await response.json());
});

loadConfig();
