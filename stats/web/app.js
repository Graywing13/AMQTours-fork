const JSON_DATA_FIELDS = [
  "songNumber",
  "songInfo.animeNames.english",
  "songInfo.animeNames.romaji",
  "songInfo.artist",
  "songInfo.composerInfo.artistId",
  "songInfo.composerInfo.name",
  "songInfo.arrangerInfo.artistId",
  "songInfo.arrangerInfo.name",
  "songInfo.songName",
  "songInfo.type",
  "songInfo.typeNumber",
  "songInfo.annId",
  "songInfo.annSongId",
  "songInfo.highRisk",
  "songInfo.animeScore",
  "songInfo.animeType",
  "songInfo.vintage",
  "songInfo.animeDifficulty",
  "songInfo.animeTags",
  "songInfo.animeGenre",
  "songInfo.altAnimeNames",
  "songInfo.altAnimeNamesAnswers",
  "songInfo.siteIds.annId",
  "songInfo.siteIds.malId",
  "songInfo.siteIds.kitsuId",
  "songInfo.siteIds.aniListId",
  "songInfo.rebroadcast",
  "songInfo.dub",
  "songInfo.seasonInfo.name",
  "songInfo.seasonInfo.number",
  "songInfo.popularityRank",
  "correctCount",
  "wrongCount",
  "videoUrl",
  "correctGuessPlayers",
  "incorrectGuessPlayers",
  "listStates",
  "codesText",
];
const JSON_DATA_COLUMN_FIELDS = JSON_DATA_FIELDS.filter((field) => field !== "codesText");
const JSON_PAYLOAD_COLUMN_INDEX = 2;
const JSON_FILE_NAME_COLUMN_INDEX = 3;
const JSON_CODES_COLUMN_INDEX = 41;

const state = {
  tours: [],
  selectedTourKey: "",
  playerSort: { column: "Guess rate", direction: "desc" },
};

const el = {
  statusText: document.getElementById("statusText"),
  configNotice: document.getElementById("configNotice"),
  tourSelect: document.getElementById("tourSelect"),
  refreshButton: document.getElementById("refreshButton"),
  summaryGrid: document.getElementById("summaryGrid"),
  playerSearch: document.getElementById("playerSearch"),
  playerCountText: document.getElementById("playerCountText"),
  playerTable: document.getElementById("playerTable"),
  highlights: document.getElementById("highlights"),
  watchedPanel: document.getElementById("watchedPanel"),
  listStats: document.getElementById("listStats"),
  songSearch: document.getElementById("songSearch"),
  songCountText: document.getElementById("songCountText"),
  songList: document.getElementById("songList"),
};

function csvUrl(sheetName) {
  const id = window.NGM_STATS_CONFIG.spreadsheetId;
  return `https://docs.google.com/spreadsheets/d/${encodeURIComponent(id)}/gviz/tq?tqx=out:csv&sheet=${encodeURIComponent(sheetName)}`;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (char === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        cell += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (char !== "\r") {
      cell += char;
    }
  }
  row.push(cell);
  rows.push(row);
  return rows.filter((items) => items.some((item) => item.trim() !== ""));
}

async function fetchCsvRows(sheetName) {
  const response = await fetch(csvUrl(sheetName), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${sheetName}: ${response.status}`);
  }
  const text = await response.text();
  if (text.trim().startsWith("<")) {
    throw new Error(`${sheetName}: sheet is not published as CSV`);
  }
  return parseCsv(text);
}

function rowsToObjects(rows) {
  if (!rows.length) return [];
  const header = rows[0].map((value) => value.trim());
  return rows.slice(1).map((row) => {
    const object = {};
    header.forEach((name, index) => {
      object[name] = row[index] ?? "";
    });
    return object;
  });
}

function parseMaybeJson(value) {
  if (!value || typeof value !== "string") return value || "";
  const text = value.trim();
  if (!text || !["[", "{"].includes(text[0])) return value;
  try {
    return JSON.parse(text);
  } catch {
    return value;
  }
}

function compactRowType(row) {
  const payload = parseMaybeJson(row[JSON_PAYLOAD_COLUMN_INDEX] || "");
  if (!Array.isArray(payload)) return "";
  if (payload.some((song) => song && typeof song === "object" && "songLabel" in song)) {
    return "blob";
  }
  return "columns";
}

function packedColumnValues(value, songCount) {
  const parsed = parseMaybeJson(value ?? "");
  if (parsed === "" || parsed === null || parsed === undefined) {
    return Array(songCount).fill("");
  }
  if (Array.isArray(parsed)) {
    if (parsed.length === songCount) return parsed;
    if (songCount === 1) return [parsed];
    const padded = parsed.slice(0, songCount);
    while (padded.length < songCount) padded.push("");
    return padded;
  }
  if (songCount === 1) return [parsed];
  return [parsed, ...Array(Math.max(0, songCount - 1)).fill("")];
}

function songsFromBlobCompactRow(row) {
  const rowFileName = row[JSON_FILE_NAME_COLUMN_INDEX] || "";
  const songs = parseMaybeJson(row[JSON_PAYLOAD_COLUMN_INDEX] || "");
  if (!Array.isArray(songs)) return [];
  return songs
    .filter((song) => song && typeof song === "object")
    .map((song) => {
      const rebuilt = {
        tourType: row[0],
        exportTime: row[1],
        songLabel: parseMaybeJson(song.songLabel ?? ""),
        fileName: song.fileName || rowFileName,
        jsonName: rowFileName || song.fileName || "",
        codesText: row[JSON_CODES_COLUMN_INDEX] || "",
      };
      JSON_DATA_COLUMN_FIELDS.forEach((field) => {
        rebuilt[field] = parseMaybeJson(song[field] ?? "");
      });
      return rebuilt;
    });
}

function songsFromColumnCompactRow(row) {
  const parsedLabels = parseMaybeJson(row[JSON_PAYLOAD_COLUMN_INDEX] || "");
  const songLabels = Array.isArray(parsedLabels)
    ? parsedLabels
    : (parsedLabels === "" || parsedLabels === null || parsedLabels === undefined ? [] : [parsedLabels]);
  const songCount = songLabels.length;
  if (!songCount) return [];

  const rowFileName = row[JSON_FILE_NAME_COLUMN_INDEX] || "";
  const packedValues = {};
  JSON_DATA_COLUMN_FIELDS.forEach((field, index) => {
    packedValues[field] = packedColumnValues(row[index + 4] ?? "", songCount);
  });

  return songLabels.map((songLabel, songIndex) => {
    const song = {
      tourType: row[0],
      exportTime: row[1],
      songLabel,
      fileName: rowFileName,
      jsonName: rowFileName,
      codesText: row[JSON_CODES_COLUMN_INDEX] || "",
    };
    JSON_DATA_COLUMN_FIELDS.forEach((field) => {
      song[field] = packedValues[field][songIndex] ?? "";
    });
    return song;
  });
}

function numberValue(value) {
  if (typeof value === "number") return value;
  if (value === null || value === undefined) return NaN;
  const cleaned = String(value).replace("%", "").replace(/,/g, "").trim();
  if (!cleaned) return NaN;
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : NaN;
}

function formatNumber(value, decimals = 2) {
  const parsed = numberValue(value);
  return Number.isFinite(parsed) ? parsed.toFixed(decimals) : "N/A";
}

function groupByTimestamp(rows, tab) {
  const groups = new Map();
  rows.forEach((row) => {
    const timestamp = row.Timestamp || row.timestamp;
    const playerName = row["Player name"];
    if (!timestamp || !playerName || timestamp === "Timestamp" || playerName === "Player name") return;
    const key = `${tab.tourType}__${timestamp}`;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        timestamp,
        tourType: tab.tourType,
        mode: tab.mode,
        sheet: tab.sheet,
        players: [],
        songs: [],
        listStats: [],
      });
    }
    groups.get(key).players.push(row);
  });
  return Array.from(groups.values());
}

function parseJsonDataRows(rows) {
  return rows.flatMap((row) => {
      if (row.length < 3 || !row[0] || !row[1]) return [];
      const rowType = compactRowType(row);
      if (rowType === "blob") return songsFromBlobCompactRow(row);
      if (rowType === "columns") return songsFromColumnCompactRow(row);
      const rowFileName = row[JSON_FILE_NAME_COLUMN_INDEX] || "";
      if (row.length < 5) return [];
      const song = {
        tourType: row[0],
        exportTime: row[1],
        songLabel: row[2],
        fileName: rowFileName,
        jsonName: rowFileName,
      };
      JSON_DATA_FIELDS.forEach((field, index) => {
        song[field] = parseMaybeJson(row[index + 4] ?? "");
      });
      return [song];
    })
}

function parseListDataRows(rows) {
  return rows
    .map((row) => {
      if (row.length < 4 || !row[0] || !row[1]) return null;
      const players = [];
      for (let index = 2; index < row.length; index += 2) {
        if (row[index]) {
          players.push({ player: row[index], average: row[index + 1] ?? "" });
        }
      }
      return { tourType: row[0], exportTime: row[1], players };
    })
    .filter(Boolean);
}

function parseChantingIds(rows) {
  return new Set(rows.slice(1).map((row) => String(row[0] || "").trim()).filter(Boolean));
}

function sameTour(row, tour) {
  return row.tourType === tour.tourType && row.exportTime === tour.timestamp;
}

function attachDetails(tours, jsonRows, listRows) {
  tours.forEach((tour) => {
    tour.songs = jsonRows.filter((row) => sameTour(row, tour));
    const listMatch = listRows.find((row) => sameTour(row, tour));
    tour.listStats = listMatch ? listMatch.players : [];
  });
}

function timestampValue(timestamp) {
  return new Date(String(timestamp).replace(" ", "T")).getTime() || 0;
}

function currentTour() {
  return state.tours.find((tour) => tour.key === state.selectedTourKey) || state.tours[0];
}

function playerName(row) {
  return row["Player name"] || row.Player || "";
}

function topRows(rows, column, reverse = true, limit = 3) {
  return rows
    .map((row) => ({ name: playerName(row), value: numberValue(row[column]) }))
    .filter((row) => row.name && Number.isFinite(row.value))
    .sort((a, b) => reverse ? b.value - a.value : a.value - b.value)
    .slice(0, limit);
}

function correctPlayers(song) {
  const value = song.correctGuessPlayers;
  if (!Array.isArray(value)) return [];
  return value.map((entry) => {
    if (typeof entry === "string") return { name: entry };
    return { name: entry.name || entry.playerName || entry.username || "", answerTime: numberValue(entry.answerTime) };
  }).filter((entry) => entry.name);
}

function listStatePlayers(song) {
  const value = song.listStates;
  if (!Array.isArray(value)) return [];
  return value.map((entry) => typeof entry === "string" ? { name: entry } : entry).filter((entry) => entry && entry.name);
}

function answerTimeRows(tour) {
  const byPlayer = new Map();
  tour.songs.forEach((song) => {
    correctPlayers(song).forEach((player) => {
      if (!Number.isFinite(player.answerTime)) return;
      if (!byPlayer.has(player.name)) byPlayer.set(player.name, []);
      byPlayer.get(player.name).push(player.answerTime);
    });
  });
  return Array.from(byPlayer.entries()).map(([name, values]) => ({
    name,
    value: values.reduce((sum, item) => sum + item, 0) / values.length,
  }));
}

function chantingRows(tour) {
  const ids = state.chantingIds || new Set();
  if (!ids.size) return { lovers: [], haters: [] };
  const seen = new Map();
  const correct = new Map();
  tour.songs.forEach((song) => {
    const annSongId = String(song["songInfo.annSongId"] || "").trim();
    if (!ids.has(annSongId)) return;
    const hitPlayers = new Set(correctPlayers(song).map((player) => player.name));
    tour.players.forEach((row) => {
      const name = playerName(row);
      seen.set(name, (seen.get(name) || 0) + 1);
      if (hitPlayers.has(name)) correct.set(name, (correct.get(name) || 0) + 1);
    });
  });
  const rates = Array.from(seen.entries()).map(([name, count]) => ({
    name,
    value: count ? (correct.get(name) || 0) / count : 0,
  }));
  return {
    lovers: rates.slice().sort((a, b) => b.value - a.value).slice(0, 3),
    haters: rates.slice().sort((a, b) => a.value - b.value).slice(0, 3),
  };
}

function listDifficultyRows(tour) {
  const byPlayer = new Map();
  tour.songs.forEach((song) => {
    const correctCount = numberValue(song.correctCount);
    listStatePlayers(song).forEach((player) => {
      if (!Number.isFinite(correctCount)) return;
      if (!byPlayer.has(player.name)) byPlayer.set(player.name, []);
      byPlayer.get(player.name).push(correctCount);
    });
  });
  return Array.from(byPlayer.entries()).map(([name, values]) => ({
    name,
    value: values.reduce((sum, item) => sum + item, 0) / values.length,
  }));
}

function setStatus(text) {
  el.statusText.textContent = text;
}

function showNotice(text) {
  el.configNotice.textContent = text;
  el.configNotice.classList.toggle("hidden", !text);
}

function renderTourSelect() {
  el.tourSelect.innerHTML = "";
  state.tours.forEach((tour) => {
    const option = document.createElement("option");
    option.value = tour.key;
    option.textContent = `${tour.timestamp} - ${tour.tourType}`;
    el.tourSelect.appendChild(option);
  });
  el.tourSelect.value = state.selectedTourKey || state.tours[0]?.key || "";
}

function renderSummary(tour) {
  const avgGr = tour.players.reduce((sum, row) => sum + (numberValue(row["Guess rate"]) || 0), 0) / Math.max(1, tour.players.length);
  const totalSongs = Math.max(...tour.players.map((row) => numberValue(row["Total songs"])).filter(Number.isFinite), 0);
  const answerTimes = answerTimeRows(tour);
  const avgAnswer = answerTimes.length
    ? answerTimes.reduce((sum, row) => sum + row.value, 0) / answerTimes.length
    : NaN;
  const metrics = [
    ["Tour Type", tour.tourType],
    ["Export Time", tour.timestamp],
    ["Players", tour.players.length],
    ["Songs", totalSongs || tour.songs.length || "N/A"],
    ["Avg GR", Number.isFinite(avgGr) ? `${avgGr.toFixed(2)}%` : "N/A"],
    ["Avg Answer", Number.isFinite(avgAnswer) ? avgAnswer.toFixed(2) : "N/A"],
  ];
  el.summaryGrid.innerHTML = metrics.map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join("");
}

function renderPlayerTable(tour) {
  const query = el.playerSearch.value.trim().toLowerCase();
  let rows = tour.players.filter((row) => playerName(row).toLowerCase().includes(query));
  const { column, direction } = state.playerSort;
  rows = rows.slice().sort((a, b) => {
    const av = numberValue(a[column]);
    const bv = numberValue(b[column]);
    if (Number.isFinite(av) && Number.isFinite(bv)) return direction === "asc" ? av - bv : bv - av;
    return direction === "asc"
      ? String(a[column] || "").localeCompare(String(b[column] || ""))
      : String(b[column] || "").localeCompare(String(a[column] || ""));
  });
  const columns = Object.keys(tour.players[0] || {}).filter((columnName) => rows.some((row) => String(row[columnName] || "").trim()));
  el.playerCountText.textContent = `${rows.length} of ${tour.players.length} players`;
  el.playerTable.innerHTML = `
    <thead><tr>${columns.map((name) => `<th data-column="${name}">${name}${state.playerSort.column === name ? (state.playerSort.direction === "asc" ? " ▲" : " ▼") : ""}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((row) => `<tr>${columns.map((name) => `<td>${row[name] || ""}</td>`).join("")}</tr>`).join("")}</tbody>
  `;
}

function renderRankCard(title, rows, formatter = (value) => formatNumber(value)) {
  const content = rows.length
    ? rows.map((row, index) => `<div class="rank-row"><b>${index + 1}. ${row.name}</b><span>${formatter(row.value)}</span></div>`).join("")
    : `<div class="rank-row"><b>No data</b><span></span></div>`;
  return `<div class="highlight-card"><h3>${title}</h3>${content}</div>`;
}

function renderHighlights(tour) {
  const answerTimes = answerTimeRows(tour);
  const chanting = chantingRows(tour);
  const listRows = listDifficultyRows(tour);
  const cards = [
    renderRankCard("Top Attackers", topRows(tour.players, "Lives taken")),
    renderRankCard("Top Blockers", topRows(tour.players, "Lives saved")),
    renderRankCard("Tryhards", answerTimes.slice().sort((a, b) => a.value - b.value).slice(0, 3)),
    renderRankCard("Ballscratchers", answerTimes.slice().sort((a, b) => b.value - a.value).slice(0, 3)),
    renderRankCard("Chanting Lovers", chanting.lovers, (value) => `${(value * 100).toFixed(2)}%`),
    renderRankCard("Chanting Haters", chanting.haters, (value) => `${(value * 100).toFixed(2)}%`),
    renderRankCard("Easiest Lists", listRows.slice().sort((a, b) => b.value - a.value).slice(0, 3)),
    renderRankCard("Hardest Lists", listRows.slice().sort((a, b) => a.value - b.value).slice(0, 3)),
    renderRankCard("Most Rigs", topRows(tour.players, "Rigs")),
  ];
  el.highlights.innerHTML = cards.join("");
}

function renderListStats(tour) {
  const hasWatchedData = tour.mode === "watched" || tour.listStats.length || tour.players.some((row) => row.Rigs || row.Onlist || row.Offlist);
  el.watchedPanel.classList.toggle("hidden", !hasWatchedData);
  if (!hasWatchedData) return;
  const listRows = tour.listStats.slice().sort((a, b) => numberValue(b.average) - numberValue(a.average));
  const cards = [
    renderRankCard("Avg Lobby Guesses On List", listRows.map((row) => ({ name: row.player, value: numberValue(row.average) }))),
    renderRankCard("Onlist GR", topRows(tour.players, "Onlist")),
    renderRankCard("Offlist GR", topRows(tour.players, "Offlist")),
    renderRankCard("Rigs Missed", topRows(tour.players, "Rigs missed")),
  ];
  el.listStats.innerHTML = `<div class="highlight-grid">${cards.join("")}</div>`;
}

function songTitle(song) {
  return song["songInfo.songName"] || song["songInfo.animeNames.english"] || song["songInfo.animeNames.romaji"] || song.songLabel || "Unknown song";
}

function renderSongs(tour) {
  const query = el.songSearch.value.trim().toLowerCase();
  const songs = tour.songs.filter((song) => {
    const haystack = [
      songTitle(song),
      song["songInfo.animeNames.english"],
      song["songInfo.animeNames.romaji"],
      song.correctGuessPlayers,
      song.incorrectGuessPlayers,
    ].map((item) => JSON.stringify(item || "")).join(" ").toLowerCase();
    return haystack.includes(query);
  });
  el.songCountText.textContent = tour.songs.length ? `${songs.length} of ${tour.songs.length} songs` : "No JsonData match for this tour";
  el.songList.innerHTML = songs.map((song) => {
    const correct = correctPlayers(song).map((player) => player.answerTime ? `${player.name} (${player.answerTime.toFixed(2)})` : player.name);
    const incorrect = Array.isArray(song.incorrectGuessPlayers) ? song.incorrectGuessPlayers : [];
    return `
      <article class="song-card">
        <div>
          <div class="song-title">${song.songLabel || ""} ${songTitle(song)}</div>
          <div class="song-meta">${song["songInfo.animeNames.english"] || song["songInfo.animeNames.romaji"] || ""}</div>
        </div>
        <div><b>Type</b><div>${song["songInfo.type"] || ""}${song["songInfo.typeNumber"] ? ` ${song["songInfo.typeNumber"]}` : ""}</div></div>
        <div><b>Difficulty</b><div>${song["songInfo.animeDifficulty"] || "N/A"}</div></div>
        <div><b>Correct</b><div>${song.correctCount || correct.length || 0}</div></div>
        <div><b>Players</b><div>${correct.slice(0, 8).map((name) => `<span class="pill">${name}</span>`).join("")}${incorrect.slice(0, 8).map((name) => `<span class="pill">${name}</span>`).join("")}</div></div>
      </article>
    `;
  }).join("");
}

function render() {
  const tour = currentTour();
  if (!tour) {
    el.summaryGrid.innerHTML = "";
    el.playerTable.innerHTML = "";
    el.highlights.innerHTML = "";
    el.songList.innerHTML = "";
    return;
  }
  renderTourSelect();
  renderSummary(tour);
  renderPlayerTable(tour);
  renderHighlights(tour);
  renderListStats(tour);
  renderSongs(tour);
}

async function loadData() {
  const config = window.NGM_STATS_CONFIG || {};
  if (!config.spreadsheetId || config.spreadsheetId.includes("PASTE_")) {
    showNotice("Set spreadsheetId in web/config.js to the published NGM Stats Export v2 spreadsheet id.");
    setStatus("Waiting for sheet configuration.");
    return;
  }
  showNotice("");
  setStatus("Loading published sheet data...");

  const statResults = await Promise.allSettled(config.statTabs.map(async (tab) => {
    const rows = await fetchCsvRows(tab.sheet);
    return groupByTimestamp(rowsToObjects(rows), tab);
  }));

  const tours = statResults.flatMap((result) => result.status === "fulfilled" ? result.value : []);

  const [jsonResult, listResult, miscResult] = await Promise.allSettled([
    fetchCsvRows(config.detailTabs.jsonData),
    fetchCsvRows(config.detailTabs.listData),
    fetchCsvRows(config.detailTabs.miscData),
  ]);

  const jsonRows = jsonResult.status === "fulfilled" ? parseJsonDataRows(jsonResult.value) : [];
  const listRows = listResult.status === "fulfilled" ? parseListDataRows(listResult.value) : [];
  state.chantingIds = miscResult.status === "fulfilled" ? parseChantingIds(miscResult.value) : new Set();

  attachDetails(tours, jsonRows, listRows);
  state.tours = tours.sort((a, b) => timestampValue(b.timestamp) - timestampValue(a.timestamp));
  state.selectedTourKey = state.tours[0]?.key || "";
  setStatus(state.tours.length ? `${state.tours.length} tours loaded.` : "No tours found in published stat tabs.");
  render();
}

el.refreshButton.addEventListener("click", loadData);
el.tourSelect.addEventListener("change", () => {
  state.selectedTourKey = el.tourSelect.value;
  render();
});
el.playerSearch.addEventListener("input", render);
el.songSearch.addEventListener("input", render);
el.playerTable.addEventListener("click", (event) => {
  const header = event.target.closest("th");
  if (!header) return;
  const column = header.dataset.column;
  if (state.playerSort.column === column) {
    state.playerSort.direction = state.playerSort.direction === "asc" ? "desc" : "asc";
  } else {
    state.playerSort = { column, direction: "desc" };
  }
  render();
});

loadData().catch((error) => {
  showNotice(error.message);
  setStatus("Could not load published sheet data.");
});
