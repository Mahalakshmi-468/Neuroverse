const $ = (id) => document.getElementById(id);

let state = null;
let typingTimer = null;
let achievementCatalog = {};

const WORLD_ICONS = {
  "Nebula Frontier": "🚀", "Lost Jurassic Valley": "🦖", "Sunken Moon Kingdom": "🐙",
  "Emerald Jungle": "🦜", "Kingdom of Luminara": "🐉", "Dunes of Sahara Prime": "🦊",
  "Frostfall Peaks": "🦉", "Circuit City": "🤖", "Shattered Reef Isles": "🏴‍☠️",
  "Emberpeak Volcano": "🌋", "Skyreach Clouds": "☁️", "Candy Cascade Valley": "🍬",
  "Hollow Manor": "👻", "The Whispering Caves": "🦇", "Neon Circuit District": "🛸",
  "Forgotten Palm Atoll": "🦀",
};

async function loadAchievementCatalog() {
  try {
    const r = await fetch("/api/achievements");
    achievementCatalog = await r.json();
  } catch (e) {
    achievementCatalog = {};
  }
}

/* ------------------------------------------------------------------ */
/* Engine badge                                                        */
/* ------------------------------------------------------------------ */
async function checkEngine() {
  const badge = $("llmBadge");
  try {
    const r = await fetch("/api/health");
    const info = await r.json();
    if (info.llm_enabled) {
      badge.textContent = `LIVE AI ENGINE • ${info.model}`;
      badge.className = "llm-badge on";
    } else {
      badge.textContent = "OFFLINE STORY ENGINE";
      badge.className = "llm-badge off";
    }
  } catch (e) {
    badge.textContent = "ENGINE UNREACHABLE";
    badge.className = "llm-badge off";
  }
}

/* ------------------------------------------------------------------ */
/* Launch screen: saved sessions                                       */
/* ------------------------------------------------------------------ */
async function loadSessionList() {
  const box = $("sessionList");
  try {
    const r = await fetch("/api/sessions");
    const list = await r.json();
    if (!list.length) {
      box.innerHTML = `<p class="muted">No missions yet. Launch your first adventure to see it here.</p>`;
      return;
    }
    box.innerHTML = "";
    list.forEach((s) => {
      const card = document.createElement("div");
      card.className = "session-card";
      card.innerHTML = `
        <div class="meta">
          <span class="world">${escapeHtml(s.world)}</span>
          <span class="sub">${escapeHtml(s.player)} • Ch.${s.chapter} • Score ${s.score}</span>
        </div>
        <span class="tag ${s.finished ? "done" : ""}">${s.finished ? "COMPLETE" : "ACTIVE"}</span>
        <button class="del" title="Delete mission" aria-label="Delete mission">✕</button>
      `;
      card.querySelector(".meta").onclick = () => resumeSession(s.session_id);
      card.querySelector(".tag").onclick = () => resumeSession(s.session_id);
      card.querySelector(".del").onclick = async (ev) => {
        ev.stopPropagation();
        await fetch(`/api/session/${s.session_id}`, { method: "DELETE" });
        loadSessionList();
      };
      box.appendChild(card);
    });
  } catch (e) {
    box.innerHTML = `<p class="error">Couldn't load saved missions. Is the server running?</p>`;
  }
}

async function resumeSession(id) {
  const r = await fetch(`/api/session/${id}`);
  if (!r.ok) return loadSessionList();
  state = await r.json();
  showGame();
  render({ typewriter: false });
}

/* ------------------------------------------------------------------ */
/* Start a new adventure                                               */
/* ------------------------------------------------------------------ */
async function start() {
  const idea = $("idea").value.trim() || "I want a fantasy adventure";
  const player = $("player").value.trim() || "Explorer";
  const btn = $("start");
  $("startError").textContent = "";
  btn.disabled = true;
  btn.textContent = "Launching…";
  try {
    const r = await fetch("/api/adventure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea, player }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || "Failed to launch mission");
    state = await r.json();
    showGame();
    render({ typewriter: true });
  } catch (e) {
    $("startError").textContent = e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Launch mission ▸";
  }
}

/* ------------------------------------------------------------------ */
/* Make a choice                                                       */
/* ------------------------------------------------------------------ */
async function makeChoice(choiceText, btn) {
  $("choiceError").textContent = "";
  clearInterval(choiceTimerInterval);
  const gotSpeedBonus = speedBonusEarned();
  document.querySelectorAll("#choices button").forEach((b) => (b.disabled = true));
  if (btn) btn.textContent = "…";
  if (gotSpeedBonus) flashSpeedBonus();
  try {
    const r = await fetch("/api/choice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.session_id, choice: choiceText }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || "Something went wrong");
    state = await r.json();
    render({ typewriter: true });
    speak(state.story);
  } catch (e) {
    $("choiceError").textContent = e.message;
    document.querySelectorAll("#choices button").forEach((b) => (b.disabled = false));
  }
}

function flashSpeedBonus() {
  const flash = document.createElement("div");
  flash.className = "speed-bonus-flash";
  flash.textContent = "⚡ Speed bonus!";
  document.body.appendChild(flash);
  setTimeout(() => flash.remove(), 900);
}

/* ------------------------------------------------------------------ */
/* Rendering                                                            */
/* ------------------------------------------------------------------ */
function showGame() {
  $("launch").classList.add("hidden");
  $("game").classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showLaunch() {
  state = null;
  $("game").classList.add("hidden");
  $("launch").classList.remove("hidden");
  loadSessionList();
}

function render({ typewriter }) {
  const icon = WORLD_ICONS[state.world] || "✦";
  $("statWorld").innerHTML = `<span class="world-icon">${icon}</span> ${escapeHtml(state.world)}`;
  $("statCompanion").textContent = state.companion;
  $("statChapter").textContent = `${state.chapter} / ${state.max_chapters}`;
  $("statScore").textContent = state.score;
  $("chapterTag").textContent = `CH. ${state.chapter}`;

  const health = Math.max(0, Math.min(100, state.health));
  const healthBar = $("healthBar");
  healthBar.style.width = `${health}%`;
  healthBar.classList.toggle("low", health <= 30);

  $("engineTag").textContent = state.source ? `• ${state.source} engine` : "";

  typeStory(state.story, typewriter);

  const isPuzzle = /riddle/i.test(state.mission || "");
  $("mission").textContent = state.mission;
  $("mission").parentElement.classList.toggle("puzzle", isPuzzle);

  const choicesBox = $("choices");
  choicesBox.innerHTML = "";
  state.choices.forEach((c, i) => {
    const b = document.createElement("button");
    b.innerHTML = `<span class="idx">${i + 1}</span> ${escapeHtml(c)}`;
    b.onclick = () => makeChoice(c, b);
    choicesBox.appendChild(b);
  });

  $("finishedNote").classList.toggle("hidden", !state.finished);

  renderTraits();
  renderInventory();
  renderAchievements();
  renderHistory();
  maybeShowAchievementToast();

  if (isPuzzle && !state.finished) {
    playGuardianMiniGame();
  } else if (!state.finished) {
    startChoiceTimer();
  }
}

/* ------------------------------------------------------------------ */
/* GAMEPLAY: choice countdown timer — rewards fast decisions            */
/* ------------------------------------------------------------------ */
let choiceTimerInterval = null;
const CHOICE_TIME_LIMIT = 12;

function startChoiceTimer() {
  clearInterval(choiceTimerInterval);
  const bar = $("choiceTimerBar");
  const label = $("choiceTimerLabel");
  if (!bar || !label) return;
  let remaining = CHOICE_TIME_LIMIT;
  const startedAt = Date.now();
  bar.style.width = "100%";
  bar.classList.remove("urgent");
  label.textContent = `⏱ ${remaining}s — quick choices earn a speed bonus!`;

  choiceTimerInterval = setInterval(() => {
    const elapsed = (Date.now() - startedAt) / 1000;
    remaining = Math.max(0, CHOICE_TIME_LIMIT - elapsed);
    bar.style.width = `${(remaining / CHOICE_TIME_LIMIT) * 100}%`;
    label.textContent = remaining > 0
      ? `⏱ ${Math.ceil(remaining)}s — quick choices earn a speed bonus!`
      : "⏱ Take your time — bonus window closed.";
    if (remaining <= 4) bar.classList.add("urgent");
    if (remaining <= 0) clearInterval(choiceTimerInterval);
  }, 100);
}

function speedBonusEarned() {
  const bar = $("choiceTimerBar");
  if (!bar) return false;
  return parseFloat(bar.style.width) > 0;
}

/* ------------------------------------------------------------------ */
/* GAMEPLAY: Guardian tap mini-game — a real reflex challenge before     */
/* the riddle chapter's choices unlock                                  */
/* ------------------------------------------------------------------ */
function playGuardianMiniGame() {
  const overlay = $("miniGameOverlay");
  const choicesBox = $("choices");
  if (!overlay) {
    startChoiceTimer();
    return;
  }
  choicesBox.classList.add("hidden");
  overlay.classList.remove("hidden");

  const target = $("miniGameTarget");
  const scoreEl = $("miniGameScore");
  const timeEl = $("miniGameTime");
  const arena = $("miniGameArena");
  let taps = 0;
  const GOAL = 5;
  const DURATION = 6;
  let timeLeft = DURATION;
  scoreEl.textContent = `0 / ${GOAL}`;
  timeEl.textContent = `${timeLeft}s`;

  function moveTarget() {
    const maxX = arena.clientWidth - target.clientWidth - 8;
    const maxY = arena.clientHeight - target.clientHeight - 8;
    target.style.left = `${Math.max(4, Math.random() * maxX)}px`;
    target.style.top = `${Math.max(4, Math.random() * maxY)}px`;
  }

  function finish(success) {
    clearInterval(countdown);
    target.onclick = null;
    $("miniGameResult").textContent = success
      ? "⚡ Guardian impressed! The path opens…"
      : "The guardian sighs and lets you pass anyway.";
    $("miniGameResult").classList.remove("hidden");
    setTimeout(() => {
      overlay.classList.add("hidden");
      $("miniGameResult").classList.add("hidden");
      choicesBox.classList.remove("hidden");
      startChoiceTimer();
    }, 1100);
  }

  target.onclick = () => {
    taps += 1;
    scoreEl.textContent = `${taps} / ${GOAL}`;
    target.classList.remove("pop");
    void target.offsetWidth;
    target.classList.add("pop");
    if (taps >= GOAL) finish(true);
    else moveTarget();
  };

  moveTarget();
  const countdown = setInterval(() => {
    timeLeft -= 1;
    timeEl.textContent = `${Math.max(0, timeLeft)}s`;
    if (timeLeft <= 0) finish(taps >= GOAL);
  }, 1000);
}

/* ------------------------------------------------------------------ */
/* GAMEPLAY: confetti burst on achievement unlock                       */
/* ------------------------------------------------------------------ */
function burstConfetti() {
  const layer = $("confettiLayer");
  if (!layer) return;
  const colors = ["#ffb84d", "#9b8cff", "#5eead4", "#ff6b6b", "#ffe66d"];
  for (let i = 0; i < 26; i++) {
    const piece = document.createElement("span");
    piece.className = "confetti-piece";
    piece.style.left = `${45 + Math.random() * 10}%`;
    piece.style.background = colors[i % colors.length];
    piece.style.setProperty("--dx", `${(Math.random() - 0.5) * 260}px`);
    piece.style.setProperty("--rot", `${Math.random() * 720 - 360}deg`);
    piece.style.animationDelay = `${Math.random() * 0.15}s`;
    layer.appendChild(piece);
    setTimeout(() => piece.remove(), 1500);
  }
}

function renderTraits() {
  const traits = state.traits || { bravery: 0, curiosity: 0, kindness: 0 };
  const pct = (v) => `${Math.max(0, Math.min(100, (v / 30) * 100))}%`;
  $("traitBravery").style.width = pct(traits.bravery || 0);
  $("traitCuriosity").style.width = pct(traits.curiosity || 0);
  $("traitKindness").style.width = pct(traits.kindness || 0);
}

function renderInventory() {
  const box = $("inventoryBox");
  const items = state.inventory || [];
  if (!items.length) {
    box.innerHTML = `<p class="muted small">Nothing collected yet.</p>`;
    return;
  }
  box.innerHTML = items.map((i) => `<span class="item-chip">${escapeHtml(i)}</span>`).join("");
}

function renderAchievements() {
  const box = $("achievementList");
  const ids = state.achievements || [];
  if (!ids.length) {
    box.innerHTML = `<p class="muted small">None unlocked yet.</p>`;
    return;
  }
  box.innerHTML = ids
    .map((id) => {
      const meta = achievementCatalog[id] || { name: id, description: "" };
      return `<div class="achievement-chip"><span class="name">★ ${escapeHtml(meta.name)}</span><span class="desc">${escapeHtml(meta.description)}</span></div>`;
    })
    .join("");
}

function maybeShowAchievementToast() {
  const fresh = state.new_achievements || [];
  if (!fresh.length) return;
  const meta = achievementCatalog[fresh[0]] || { name: fresh[0] };
  const toast = $("achievementToast");
  $("achievementToastName").textContent = meta.name;
  toast.classList.add("show");
  burstConfetti();
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove("show"), 3200);
}

function renderHistory() {
  const log = $("historyLog");
  log.innerHTML = "";
  state.history.forEach((h) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="ch">Chapter ${h.chapter}</span>${escapeHtml(h.choice)}`;
    log.appendChild(li);
  });
  if (state.finished) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="ch">Chapter ${state.chapter}</span>Mission complete`;
    log.appendChild(li);
  }
}

function typeStory(text, animate) {
  clearInterval(typingTimer);
  const el = $("story");
  if (!animate) {
    el.textContent = text;
    return;
  }
  el.textContent = "";
  let i = 0;
  typingTimer = setInterval(() => {
    el.textContent = text.slice(0, i);
    i += 3;
    if (i > text.length) {
      el.textContent = text;
      clearInterval(typingTimer);
    }
  }, 12);
}

/* ------------------------------------------------------------------ */
/* Speech (browser APIs, both optional)                                */
/* ------------------------------------------------------------------ */
function speak(text) {
  if ("speechSynthesis" in window) {
    speechSynthesis.cancel();
    speechSynthesis.speak(new SpeechSynthesisUtterance(text));
  }
}

function setupVoiceInput() {
  $("voice").onclick = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      $("voiceStatus").textContent = "Voice input isn't supported in this browser — type your idea instead.";
      return;
    }
    const r = new SR();
    r.lang = "en-IN";
    $("voiceStatus").textContent = "Listening…";
    r.onresult = (e) => {
      $("idea").value = e.results[0][0].transcript;
      $("voiceStatus").textContent = "Idea captured.";
    };
    r.onerror = () => ($("voiceStatus").textContent = "Voice input failed — please type your idea.");
    r.start();
  };
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/* ------------------------------------------------------------------ */
/* Wire up                                                              */
/* ------------------------------------------------------------------ */
$("start").onclick = start;
$("speakStory").onclick = () => state && speak(state.story);
$("newMission").onclick = showLaunch;
setupVoiceInput();
checkEngine();
loadSessionList();
loadAchievementCatalog();
