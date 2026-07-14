const searchInput = document.getElementById("search-input");
const suggestionsList = document.getElementById("suggestions");
const selectedList = document.getElementById("selected-games");
const mineButton = document.getElementById("mine-button");
const hiddenGemsOnlyCheckbox = document.getElementById("hidden-gems-only");
const resultsSection = document.getElementById("results");

let maxSelectedGames = 5;
let selectedGames = [];
let searchDebounceTimer = null;

function igdbCoverUrl(imageId, size) {
  if (!imageId) return null;
  return `https://images.igdb.com/igdb/image/upload/t_${size}/${encodeURIComponent(imageId)}.jpg`;
}

function releaseYear(isoDate) {
  return isoDate ? new Date(isoDate).getFullYear() : null;
}

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
    item.className = "suggestion";

    const coverUrl = igdbCoverUrl(game.cover_image_id, "cover_small");
    if (coverUrl) {
      const cover = document.createElement("img");
      cover.className = "cover-thumb";
      cover.src = coverUrl;
      cover.alt = "";
      item.appendChild(cover);
    }

    const label = document.createElement("span");
    const year = releaseYear(game.first_release_date);
    label.textContent = year ? `${game.name} (${year})` : game.name;
    item.appendChild(label);

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

    const coverUrl = igdbCoverUrl(game.cover_image_id, "cover_big");
    if (coverUrl) {
      const cover = document.createElement("img");
      cover.className = "cover-big";
      cover.src = coverUrl;
      cover.alt = "";
      card.appendChild(cover);
    }

    const body = document.createElement("div");
    body.className = "game-card-body";

    const title = document.createElement("h3");
    const year = releaseYear(game.first_release_date);
    title.textContent = year ? `${game.name} (${year})` : game.name;
    body.appendChild(title);

    const genres = document.createElement("div");
    genres.className = "genres";
    genres.textContent = game.genres.join(", ");
    body.appendChild(genres);

    const summary = document.createElement("p");
    summary.textContent = game.summary ?? "";
    body.appendChild(summary);

    card.appendChild(body);
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
    body: JSON.stringify({
      game_ids: selectedGames.map((g) => g.game_id),
      hidden_gems_only: hiddenGemsOnlyCheckbox.checked,
    }),
  });
  if (!response.ok) {
    const error = await response.json();
    resultsSection.innerHTML = `<p class="error">${error.detail}</p>`;
    return;
  }
  renderResults(await response.json());
});

loadConfig();
