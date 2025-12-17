// Simple helper to fetch leaderboards and render minimal UI
async function fetchGlobalLeaderboard() {
  try {
    const res = await fetch('/api/leaderboard/global');
    const data = await res.json();
    return data.leaderboard;
  } catch (e) {
    console.error('Failed to fetch leaderboard', e);
    return [];
  }
}

async function fetchLeagueLeaderboard(leagueId) {
  try {
    const res = await fetch(`/api/leaderboard/league/${leagueId}`);
    const data = await res.json();
    return data.leaderboard;
  } catch (e) {
    console.error('Failed to fetch league leaderboard', e);
    return [];
  }
}

// Example: render top N into a container with id
export async function renderGlobalTop(containerId, limit = 10) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const lb = await fetchGlobalLeaderboard();
  container.innerHTML = '';
  lb.slice(0, limit).forEach((entry, i) => {
    const row = document.createElement('div');
    row.className = 'leaderboard-row';
    row.innerHTML = `<strong>#${i+1} ${entry.username}</strong> — ${entry.total_value.toLocaleString(undefined, {style:'currency', currency:'USD'})} (<span class="${entry.return_percent>=0? 'text-success':'text-danger'}">${entry.return_percent}%</span>)`;
    container.appendChild(row);
  });
}
