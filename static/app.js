/* Coding Plan 额度看板 · 前端（原生 JS，无依赖）。数据通过 /api/accounts 读写。 */
'use strict';

/* ===================== 图标 ===================== */
const ICONS = {
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeoff: '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7"/><polyline points="21 3 21 9 15 9"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m2 7 10 7 10-7"/>',
  at: '<circle cx="12" cy="12" r="4"/><path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-3.92 7.94"/>',
  phone: '<rect x="7" y="2" width="10" height="20" rx="2"/><line x1="11" y1="18" x2="13" y2="18"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  key: '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  checkcircle: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
  alert: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  xcircle: '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
  ban: '<circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>',
  info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  gauge: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
  user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  note: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>',
  moon: '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  minus: '<line x1="5" y1="12" x2="19" y2="12"/>',
};
const icon = (n, cls = '') => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n]}</svg>`;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ===================== 常量 ===================== */
const DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const LOW_USED = 80;      // 已用 ≥ 80% 视为「紧张」
const SOON_DAYS = 5;      // 5 天内到期视为「即将到期」
const STATUS = {
  ok:        { label: '可用',   icon: 'checkcircle' },
  low:       { label: '紧张',   icon: 'alert' },
  exhausted: { label: '耗尽',   icon: 'xcircle' },
  reset:     { label: '已重置', icon: 'refresh' },
  expired:   { label: '已到期', icon: 'ban' },
};
// 服务商色卡：常见名字固定配色；数据里出现的其它服务商按名称顺序从备用色卡里领一个（同一份数据里稳定）
const PROVIDER_COLORS = { claude: '#e8743b', anthropic: '#e8743b', chatgpt: '#6d5ce7', openai: '#6d5ce7', codex: '#6d5ce7', gemini: '#d9538f', google: '#d9538f', copilot: '#4b8ad6', cursor: '#b8860b', kimi: '#1f9bcf', deepseek: '#4f6bed', qwen: '#7c3aed', windsurf: '#0ea5a4', trae: '#c2410c' };
const PROVIDER_FALLBACK = ['#0f766e', '#a21caf', '#b45309', '#1d4ed8', '#be123c', '#4d7c0f', '#6b7280'];
// 时间线里服务商的排列顺序：Claude 最上，ChatGPT 其次……不在表里的按名称排在最后
const PROVIDER_RANK = { claude: 0, anthropic: 0, chatgpt: 1, openai: 1, codex: 1, gemini: 2, google: 2, copilot: 3, cursor: 4, kimi: 5, deepseek: 6, qwen: 7, windsurf: 8, trae: 9 };
const provRank = p => { const k = String(p || '').trim().toLowerCase(); return k in PROVIDER_RANK ? PROVIDER_RANK[k] : 99; };
let providerOrder = [];
function refreshProviderOrder() {
  providerOrder = [...new Set(accounts.map(a => String(a.provider || '').trim().toLowerCase()).filter(k => k && !PROVIDER_COLORS[k]))].sort();
}
function provColor(p) {
  const k = String(p || '').trim().toLowerCase();
  if (PROVIDER_COLORS[k]) return PROVIDER_COLORS[k];
  const i = providerOrder.indexOf(k);
  return i < 0 ? '#8a9a94' : PROVIDER_FALLBACK[i % PROVIDER_FALLBACK.length];
}
const SHARED = '全部';                                   // 用户标签为空 = 共享账号，所有人可见
const ownerOf = a => String(a.owner || '').trim();
const normalizeOwner = v => { v = String(v || '').trim(); return (v === SHARED || v === '共享') ? '' : v; };
const H = 3600e3, D = 24 * H;
const pad = n => String(n).padStart(2, '0');
const dateStr = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const nowLocalStr = () => { const d = new Date(); return `${dateStr(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}`; };   // datetime-local 控件的值格式
const toLocalInput = s => (s.includes('T') ? s.slice(0, 16) : s + 'T00:00');                                              // 旧数据只有日期时补 00:00
const parseLocal = s => new Date(s.includes('T') ? s : s + 'T00:00');                                                       // 不带时区 → 按本地时间解析

/* ===================== 状态 ===================== */
let accounts = [];
let health = null;
let view = 'cards';
let sortBy = 'provider';
let filterProvider = '';
let filterOwner = '';
const revealed = new Set();
// 记住排序 / 视图 / 筛选（仅本浏览器）
const PREF_KEY = 'quotaboard.prefs';
function loadPrefs() {
  try {
    const p = JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
    if (['provider', 'reset', 'expiry'].includes(p.sortBy)) sortBy = p.sortBy;
    if (['cards', 'table'].includes(p.view)) view = p.view;
    if (typeof p.filterOwner === 'string') filterOwner = p.filterOwner;
    if (typeof p.filterProvider === 'string') filterProvider = p.filterProvider;
  } catch { /* 私密模式等 */ }
  // 网址里的 ?user=名字 / ?provider=名字 优先：每个人可以收藏自己的地址
  const q = new URLSearchParams(location.search);
  if (q.has('user')) filterOwner = q.get('user').trim();
  if (q.has('provider')) filterProvider = q.get('provider').trim();
}
function savePrefs() {
  try { localStorage.setItem(PREF_KEY, JSON.stringify({ sortBy, view, filterOwner, filterProvider })); } catch { /* ignore */ }
  syncUrl();
}
function syncUrl() {   // 地址栏跟着筛选走，随时可以复制 / 收藏
  const q = new URLSearchParams();
  if (filterOwner) q.set('user', filterOwner);
  if (filterProvider) q.set('provider', filterProvider);
  const qs = q.toString();
  const next = location.pathname + (qs ? '?' + qs : '') + location.hash;
  if (next !== location.pathname + location.search + location.hash) history.replaceState(null, '', next);
}

/* ===================== API ===================== */
async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {                       // 会话过期 / 未登录：回登录页
    location.href = '/login';
    throw new Error('未登录');
  }
  let data = null;
  try { data = await res.json(); } catch { /* 无 JSON 体 */ }
  if (!res.ok) throw new Error((data && data.error) || `${res.status} ${res.statusText}`);
  return data;
}
async function load() {
  try {
    const [list, h] = await Promise.all([api('GET', '/api/accounts'), api('GET', '/api/health')]);
    accounts = list.accounts || [];
    health = h;
    render();
  } catch (e) {
    toast(`加载失败：${e.message}`);
  }
}
function replaceLocal(saved) {
  const i = accounts.findIndex(a => a.id === saved.id);
  if (i >= 0) accounts[i] = saved; else accounts.push(saved);
}
async function saveAccount(id, data) {
  const saved = id ? await api('PUT', `/api/accounts/${id}`, data) : await api('POST', '/api/accounts', data);
  replaceLocal(saved);
  render();
  return saved;
}
async function setUsed(id, used) {
  replaceLocal(await api('PUT', `/api/accounts/${id}`, { used }));
  render();
}
async function deleteAccount(id) {
  await api('DELETE', `/api/accounts/${id}`);
  accounts = accounts.filter(a => a.id !== id);
  render();
}

/* ===================== 派生计算 ===================== */
function nextReset(acc, now = new Date()) {
  const [hh, mm] = String(acc.resetTime || '00:00').split(':').map(Number);
  const d = new Date(now);
  d.setHours(hh || 0, mm || 0, 0, 0);
  const todayIso = ((now.getDay() + 6) % 7) + 1;           // 周一=1 … 周日=7
  d.setDate(d.getDate() + (((acc.resetDay || 1) - todayIso + 7) % 7));
  if (d <= now) d.setDate(d.getDate() + 7);
  return d;
}
function addMonths(date, n) {
  const d = new Date(date); const day = d.getDate();
  d.setMonth(d.getMonth() + n);
  if (d.getDate() !== day) d.setDate(0);                     // 1/31 + 1 月 → 2/28
  return d;
}
function derive(acc, now = new Date()) {
  const next = nextReset(acc, now);
  const last = new Date(next.getTime() - 7 * D);
  const updated = acc.quotaUpdatedAt ? new Date(acc.quotaUpdatedAt) : null;
  const inferredReset = !!updated && updated < last;       // 记录早于最近一次重置点
  const usedEff = inferredReset ? 0 : (acc.used || 0);
  const subStart = acc.subStart ? parseLocal(acc.subStart) : null;
  const subEnd = subStart && !isNaN(subStart) ? addMonths(subStart, 1) : null;
  const daysLeft = subEnd ? Math.ceil((subEnd - now) / D) : null;
  const expired = !!subEnd && subEnd <= now;                 // 到期优先级最高：到期后有额度也不可用
  const expiringSoon = !expired && daysLeft != null && daysLeft <= SOON_DAYS;
  const status = expired ? 'expired' : inferredReset ? 'reset' : usedEff >= 100 ? 'exhausted' : usedEff >= LOW_USED ? 'low' : 'ok';
  const deadline = expired ? null : (subEnd && subEnd < next ? subEnd : next);   // 最先到来的到期 / 重置
  const deadlineType = deadline && deadline === subEnd ? 'expiry' : 'reset';
  return { ...acc, next, last, updated, inferredReset, usedEff, subStart, subEnd, daysLeft, expired, expiringSoon, status, deadline, deadlineType };
}
function sortedList() {
  let list = accounts.map(a => derive(a));
  if (filterOwner) list = list.filter(a => !ownerOf(a) || ownerOf(a) === filterOwner);   // 共享账号在任何用户下都显示
  if (filterProvider) list = list.filter(a => a.provider === filterProvider);
  // 排序只看账号自身属性（服务商、订阅起始、重置时刻、订阅到期），与已用额度无关，拖动进度条不会改变位置
  const bySubStart = (a, b) => String(a.subStart || '').localeCompare(String(b.subStart || '')) || a.id - b.id;   // 起始早的在前，再按录入先后
  const byProvider = (a, b) => provRank(a.provider) - provRank(b.provider) || String(a.provider || '').localeCompare(String(b.provider || ''), 'zh-Hans-CN');
  const CMP = {
    provider: (a, b) => byProvider(a, b) || bySubStart(a, b),
    reset:    (a, b) => a.next - b.next || bySubStart(a, b),
    expiry:   (a, b) => (a.subEnd || Infinity) - (b.subEnd || Infinity) || bySubStart(a, b),
  };
  const cmp = CMP[sortBy] || CMP.provider;
  list.sort((a, b) => (a.expired - b.expired) || cmp(a, b));   // 已到期的沉底
  const rec = list.filter(a => !a.expired && a.usedEff < 100).sort((a, b) => a.deadline - b.deadline)[0];
  list.forEach(a => { a.recommended = !!rec && a.id === rec.id; });
  return list;
}
function groupByOwner(list) {
  const groups = new Map();
  list.forEach(a => { const k = ownerOf(a) || SHARED; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(a); });
  const keys = [...groups.keys()].sort((a, b) => (b === SHARED) - (a === SHARED) || a.localeCompare(b, 'zh-Hans-CN'));   // 共享组排最前
  return keys.map(k => [k, groups.get(k)]);
}
const groupIcon = k => icon(k === SHARED ? 'users' : 'user', 'sm');
function groupStats(g) {
  const act = g.filter(a => !a.expired);
  const avail = act.filter(a => a.status === 'ok' || a.status === 'reset').length;
  const avg = act.length ? Math.round(act.reduce((s, a) => s + a.usedEff, 0) / act.length) : 0;
  return { act: act.length, avail, avg, expired: g.length - act.length };
}

/* ===================== 格式化 ===================== */
function fmtCountdown(ms, short = false) {
  const m = Math.max(0, Math.round(ms / 60000));
  const d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), mm = m % 60;
  let s;
  if (d > 0) s = `${d} 天 ${h} 小时`;
  else if (h > 0) s = short ? `${h} 小时` : `${h} 小时 ${mm} 分`;
  else s = `${mm} 分钟`;
  return short ? s : s + '后';
}
function fmtRel(date) {
  const m = Math.round((Date.now() - date) / 60000);
  if (m < 1) return '刚刚';
  if (m < 60) return `${m} 分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} 小时前`;
  return `${Math.floor(h / 24)} 天前`;
}
const fmtReset = a => `${DAYS[(a.resetDay || 1) - 1]} ${a.resetTime}`;
const fmtDate = d => `${d.getMonth() + 1}/${d.getDate()}`;
const fmtDT = d => `${fmtDate(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;

/* ===================== 渲染：总览 ===================== */
function renderOverview(list) {
  const now = Date.now();
  const active = list.filter(a => !a.expired);
  const totalUsed = active.reduce((s, a) => s + a.usedEff, 0);
  const overall = active.length ? Math.round(totalUsed / active.length) : 0;
  const counts = { ok: 0, low: 0, exhausted: 0, reset: 0, expired: 0 };
  list.forEach(a => counts[a.status]++);
  const avail = counts.ok + counts.reset;
  const soonest = [...active].sort((a, b) => a.next - b.next)[0];
  const expiring = active.filter(a => a.expiringSoon).sort((a, b) => a.subEnd - b.subEnd);
  const rec = list.find(a => a.recommended);
  const ringCls = overall >= 100 ? 's-exhausted' : overall >= LOW_USED ? 's-low' : 's-ok';
  const C = 2 * Math.PI * 52;

  document.getElementById('overview').innerHTML = `
    <div class="card hero">
      <div class="ring ${ringCls}">
        <svg viewBox="0 0 120 120"><circle class="rt" cx="60" cy="60" r="52"/><circle class="rf" cx="60" cy="60" r="52" stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${(C * (1 - overall / 100)).toFixed(1)}"/></svg>
        <div class="num"><span>${overall}<small>%</small></span></div>
      </div>
      <div class="body">
        <div class="label">总体已用额度${filterOwner ? ` · ${esc(filterOwner)}` : ''}</div>
        <div class="big">${active.length} 个有效账号<small>折合已用 ${(totalUsed / 100).toFixed(1)} / ${active.length} 份</small></div>
        <div class="segbar">${list.map(a => `<div class="seg s-${a.status}" data-goto="${a.id}" title="${esc(a.name)} · 已用 ${a.usedEff}%${a.expired ? ' · 已到期' : ''}"><i style="width:${a.usedEff}%"></i></div>`).join('')}</div>
        <div class="legend">
          <span><i class="dot s-ok"></i>可用 <b>${counts.ok}</b></span>
          <span><i class="dot s-low"></i>紧张 <b>${counts.low}</b></span>
          <span><i class="dot s-exhausted"></i>耗尽 <b>${counts.exhausted}</b></span>
          <span><i class="dot s-reset"></i>已重置 <b>${counts.reset}</b></span>
          <span><i class="dot s-expired"></i>已到期 <b>${counts.expired}</b></span>
        </div>
      </div>
    </div>
    <div class="card tile">
      <div class="label">可用账号</div>
      <div class="value">${avail}<small>/ ${active.length}</small></div>
      <div class="sub">紧张 ${counts.low} · 耗尽 ${counts.exhausted} · 已到期 ${counts.expired}</div>
    </div>
    <div class="card tile">
      <div class="label">最近一次重置</div>
      <div class="value">${soonest ? fmtCountdown(soonest.next - now, true) : '—'}<small>${soonest ? '后' : ''}</small></div>
      <div class="sub">${soonest ? `${esc(soonest.name)} · ${fmtReset(soonest)} · ${STATUS[soonest.status].label}` : '无有效账号'}</div>
    </div>
    <div class="card tile">
      <div class="label">即将到期</div>
      <div class="value">${expiring.length ? fmtCountdown(expiring[0].subEnd - now, true) : '—'}<small>${expiring.length ? '后' : ''}</small></div>
      <div class="sub">${expiring.length ? `${esc(expiring[0].name)} ${fmtDT(expiring[0].subEnd)} 到期 · ${SOON_DAYS} 天内共 ${expiring.length} 个` : `${SOON_DAYS} 天内没有订阅到期`}</div>
    </div>
    <div class="card tile">
      <div class="label">建议优先使用</div>
      <div class="value">${rec ? esc(rec.name) : '—'}</div>
      <div class="sub">${rec ? `已用 ${rec.usedEff}% · ${fmtCountdown(rec.deadline - now)}${rec.deadlineType === 'expiry' ? '到期' : '重置'}，先用掉` : '没有可用额度'}</div>
    </div>`;
}

/* ===================== 渲染：泳道时间线（SVG，今天 → 最后一个订阅到期） ===================== */
const TL = { scale: 150, pendingScroll: null, AX: 44, LH: 48, GH: 26, LABEL_W: 212, start: null, W: 0 };   // GH = 服务商分组标题行高
const SCALES = [90, 150, 240];
const dia = (x, y) => `M${x},${y - 6}L${x + 6},${y}L${x},${y + 6}L${x - 6},${y}Z`;

function renderTimeline(list) {
  const host = document.getElementById('timeline');
  const prev = host.querySelector('.tl-scroll');
  const captured = prev ? prev.scrollLeft : null;

  const now = new Date();
  const start = new Date(now); start.setHours(0, 0, 0, 0);
  const active = list.filter(a => !a.expired);
  const lastEnd = active.reduce((m, a) => Math.max(m, a.subEnd ? a.subEnd.getTime() : 0), 0);
  const totalDays = Math.ceil((Math.max(start.getTime() + 8 * D, lastEnd + D) - start.getTime()) / D);
  const W = totalDays * TL.scale;
  // 先按服务商分组（Claude → ChatGPT → …），组内已到期沉底、再按最先到来的到期 / 重置
  const lanes = [...list].sort((a, b) => provRank(a.provider) - provRank(b.provider)
    || String(a.provider || '').localeCompare(String(b.provider || ''), 'zh-Hans-CN')
    || (a.expired - b.expired) || (a.deadline - b.deadline));
  const rows = [];
  let lastProv = null;
  for (const a of lanes) {
    const p = a.provider || '未填';
    if (p !== lastProv) { rows.push({ type: 'head', provider: p, n: lanes.filter(x => (x.provider || '未填') === p).length }); lastProv = p; }
    rows.push({ type: 'lane', a });
  }
  let yCursor = TL.AX;
  rows.forEach(r => { r.y = yCursor; yCursor += r.type === 'head' ? TL.GH : TL.LH; });
  const Hh = Math.max(yCursor, TL.AX + TL.LH);
  const x = t => (t - start) / D * TL.scale;
  const showHours = TL.scale >= 120;
  TL.start = start; TL.W = W;

  let g = '';
  for (let i = 0; i < totalDays; i++) {
    const d = new Date(start.getTime() + i * D); const X = i * TL.scale;
    const wd = (d.getDay() + 6) % 7;
    if (wd >= 5) g += `<rect class="band-weekend" x="${X}" y="0" width="${TL.scale}" height="${Hh}"/>`;
    if (i === 0) g += `<rect class="band-today" x="${X}" y="0" width="${TL.scale}" height="${Hh}"/>`;
    g += `<line class="grid-day ${wd === 0 ? 'week' : ''}" x1="${X}" x2="${X}" y1="0" y2="${Hh}"/>`;
    const lbl = i === 0 ? '今天' : i === 1 ? '明天' : DAYS[wd];
    g += `<text class="ax-day ${i === 0 ? 'today' : ''}" x="${X + 7}" y="15">${lbl}<tspan class="d"> ${i < 2 ? DAYS[wd] + ' ' : ''}${fmtDate(d)}</tspan></text>`;
    for (const h of [6, 12, 18]) {
      const hx = X + h / 24 * TL.scale;
      g += `<line class="grid-hour" x1="${hx}" x2="${hx}" y1="${TL.AX - 6}" y2="${TL.AX}"/>`;
      if (showHours) g += `<text class="ax-hour" x="${hx + 2}" y="${TL.AX - 9}">${pad(h)}</text>`;
    }
  }
  g += `<line class="ax-base" x1="0" x2="${W}" y1="${TL.AX}" y2="${TL.AX}"/>`;
  g += `<rect class="past" x="0" y="${TL.AX}" width="${x(now)}" height="${Hh - TL.AX}"/>`;

  rows.forEach(row => {                       // 注意：泳道内部用 r 表示重置时刻，这里参数不能也叫 r
    if (row.type === 'head') {
      g += `<rect class="band-group" x="0" y="${row.y}" width="${W}" height="${TL.GH}" style="fill:color-mix(in oklab, ${provColor(row.provider)} 9%, var(--surface))"/>`;
      g += `<line class="lane-sep" x1="0" x2="${W}" y1="${row.y + TL.GH}" y2="${row.y + TL.GH}"/>`;
      return;
    }
    const a = row.a;
    const y0 = row.y, cy = y0 + 29, barY = y0 + 21, barH = 16, ly = y0 + 13;
    g += `<line class="lane-sep" x1="0" x2="${W}" y1="${y0 + TL.LH}" y2="${y0 + TL.LH}"/>`;
    if (a.expired) { g += `<text class="muted-text" x="10" y="${cy + 4}">订阅已于 ${fmtDT(a.subEnd)} 到期 · 之后有额度也不可用，续订后继续</text>`; return; }
    const endT = a.subEnd ? a.subEnd.getTime() : start.getTime() + totalDays * D;   // 到期即截止
    let lane = `<g class="lane s-${a.status}">`;
    if (a.last >= start) lane += `<path class="dia past-dia" d="${dia(x(a.last), cy)}"><title>${esc(a.name)} · 已于 ${fmtDT(a.last)} 重置</title></path>`;
    let wStart = a.last.getTime(), r = a.next.getTime(), idx = 0;
    while (wStart < endT) {
      const wEnd = Math.min(r, endT);
      const x1 = Math.max(0, x(wStart)), x2 = x(wEnd);
      lane += `<rect class="win ${idx === 0 ? 'cur' : 'future'}" x="${x1}" y="${barY}" width="${Math.max(0, x2 - x1)}" height="${barH}" rx="5"/>`;
      if (idx === 0) {                       // 当前周期标「已用 X%」：条够宽写在条里，不够宽写在条右侧
        const inside = x2 - x1 > 96;
        lane += `<text class="win-text" x="${inside ? x1 + (a.last >= start ? 14 : 8) : x2 + 12}" y="${cy + 4}">已用 ${a.usedEff}%</text>`;
      }
      if (r < endT) {
        const rx = x(r), flip = rx > W - 180;
        lane += `<path class="dia" d="${dia(rx, cy)}"><title>${esc(a.name)} · ${fmtReset(a)} 重置 · ${fmtCountdown(r - now)}</title></path>`;
        const txt = idx === 0 ? `${fmtReset(a)}<tspan class="cd"> · ${fmtCountdown(r - now)}</tspan>` : `${fmtDate(new Date(r))} ${a.resetTime}`;
        lane += `<text class="rlabel" x="${flip ? rx - 9 : rx + 9}" y="${ly}" text-anchor="${flip ? 'end' : 'start'}">${txt}</text>`;
      }
      wStart = r; r += 7 * D; idx++;
    }
    if (a.subEnd) {
      const ex = x(endT);
      lane += `<line class="exp" x1="${ex}" x2="${ex}" y1="${y0 + 6}" y2="${y0 + TL.LH - 6}"><title>${esc(a.name)} 订阅 ${fmtDT(a.subEnd)} 到期</title></line>`;
      lane += `<text class="exp-text" x="${ex - 5}" y="${ly}" text-anchor="end">到期 ${fmtDT(a.subEnd)}</text>`;
    }
    g += lane + `</g>`;
  });
  if (!lanes.length) g += `<text class="muted-text" x="10" y="${TL.AX + 30}">没有账号</text>`;

  const nx = x(now);
  g += `<line class="now" x1="${nx}" x2="${nx}" y1="0" y2="${Hh}"/>`;
  g += `<g class="chip now-chip" transform="translate(${nx + 4}, 23)"><rect rx="4" height="18" width="70"/><text x="6" y="13">现在 ${pad(now.getHours())}:${pad(now.getMinutes())}</text></g>`;
  g += `<g class="xh-g" style="display:none"><line class="xh" y1="0" y2="${Hh}"/><g class="chip xh-chip"><rect rx="4" height="18" width="100"/><text x="6" y="13"></text></g></g>`;

  const labels = rows.map(r => r.type === 'head'
    ? `<div class="tl-group" style="height:${TL.GH}px;background:color-mix(in oklab, ${provColor(r.provider)} 9%, var(--surface))"><i class="pdot" style="--pcolor:${provColor(r.provider)}"></i>${esc(r.provider)}<span class="n">${r.n}</span></div>`
    : `<div class="tl-label s-${r.a.status}" style="height:${TL.LH}px" data-goto="${r.a.id}">
      <div class="txt"><div class="nm">${esc(r.a.name)}<span class="own">${esc(ownerOf(r.a) || SHARED)}</span></div><div class="pv"><i class="pdot" style="--pcolor:${provColor(r.a.provider)}"></i>${esc(r.a.provider || '未填')}</div></div>
      ${r.a.expired ? `<span class="pill xs" style="margin-left:auto">${icon('ban', 'sm')}已到期</span>` : ''}
    </div>`).join('');

  host.innerHTML = `
    <div class="tl-head">
      <div><h2>重置与到期时间线</h2></div>
      <div class="tl-legend">
        <span><i class="lg-dia"></i>重置时刻（按状态着色）</span>
        <span><i class="lg-bar cur"></i>当前额度周期</span>
        <span><i class="lg-bar fut"></i>之后的周期</span>
        <span><i class="lg-exp"></i>订阅到期</span>
        <span><i class="lg-now"></i>现在</span>
      </div>
      <div class="tl-ctl">
        <button class="btn xs" data-tl="now">${icon('target', 'sm')}回到现在</button>
        <button class="icon-btn md" data-tl="zoom-" title="缩小">${icon('minus', 'sm')}</button>
        <span class="tl-scale">${TL.scale} px / 天</span>
        <button class="icon-btn md" data-tl="zoom+" title="放大">${icon('plus', 'sm')}</button>
      </div>
    </div>
    <div class="tl-scroll"><div class="tl tl-inner">
      <div class="tl-labels" style="width:${TL.LABEL_W}px"><div class="tl-corner" style="height:${TL.AX}px">账号 · 用户</div>${labels}</div>
      <svg width="${W}" height="${Hh}" viewBox="0 0 ${W} ${Hh}">${g}</svg>
    </div></div>`;

  host.querySelectorAll('svg g.chip').forEach(c => { const t = c.querySelector('text'); if (t.textContent) c.querySelector('rect').setAttribute('width', Math.ceil(t.getBBox().width) + 12); });
  const scroller = host.querySelector('.tl-scroll');
  scroller.scrollLeft = TL.pendingScroll ?? captured ?? 0;
  TL.pendingScroll = null;
}

/* ===================== 渲染：账号分组 / 列表 ===================== */
function chipsHTML(a, compact = false) {
  const mk = (ic, text, title, copy) => `<button class="chip ${compact ? 'icon-only' : ''}" title="${esc(title)}（点击复制）" data-copy="${esc(copy)}">${icon(ic, 'sm')}${compact ? '' : esc(text)}</button>`;
  const chips = [];
  if (a.mailPlatform)  chips.push(mk('mail',    a.mailPlatform,  `邮件接码平台：${a.mailPlatform}`, a.mailPlatform));
  if (a.recoveryEmail) chips.push(mk('at',      a.recoveryEmail, `辅助邮箱：${a.recoveryEmail}`,    a.recoveryEmail));
  if (a.phone)         chips.push(mk('phone',   a.phone,         `手机号：${a.phone}`,              a.phone));
  if (a.smsPlatform)  chips.push(mk('message', a.smsPlatform,  `短信接码平台：${a.smsPlatform}`,  a.smsPlatform));
  if (a.totp)         chips.push(mk('shield',  '2FA',          `2FA：${a.totp}`,                 a.totp));
  return chips.join('');
}
function pwHTML(a) {
  const shown = revealed.has(a.id);
  return `<span class="chip pw ${shown ? 'shown' : ''}">${icon('key', 'sm')}${shown ? esc(a.password) : '••••••••'}</span>
    <button class="icon-btn" data-toggle-pw="${a.id}" title="${shown ? '隐藏密码' : '显示密码'}">${icon(shown ? 'eyeoff' : 'eye', 'sm')}</button>
    <button class="icon-btn" data-copy="${esc(a.password)}" title="复制密码">${icon('copy', 'sm')}</button>`;
}
const pillHTML = a => `<span class="pill">${icon(STATUS[a.status].icon, 'sm')}${STATUS[a.status].label}</span>`;
const provHTML = a => `<span class="prov" style="--pcolor:${provColor(a.provider)}"><i></i>${esc(a.provider || '未填')}</span>`;
const sharedHTML = a => ownerOf(a) ? '' : `<span class="prov" title="共享账号：不归属任何用户，所有人可见">${icon('users', 'sm')}${SHARED}</span>`;
const tagHTML  = a => a.recommended ? `<span class="tag">${icon('star', 'sm')}建议优先</span>` : '';
function subLine(a) {
  if (!a.subEnd) return `<span class="faint">未填订阅开始日期</span>`;
  const range = `订阅 ${fmtDT(a.subStart)} 至 ${fmtDT(a.subEnd)}`;
  if (a.expired) return `${range}<span class="spacer"></span><span class="crit">已到期</span>`;
  if (a.expiringSoon) return `${range}<span class="spacer"></span><span class="pill xs s-low">${icon('alert', 'sm')}${a.daysLeft <= 1 ? '今天' : `${a.daysLeft} 天后`}到期</span>`;
  return `${range}<span class="spacer"></span><span class="faint">剩余 ${a.daysLeft} 天</span>`;
}
function actionsHTML(a, compact = false) {
  const primary = a.expired
    ? `<button class="btn sm" data-renew="${a.id}">${compact ? '' : icon('calendar', 'sm')}续订</button>`
    : a.inferredReset
      ? `<button class="btn sm" data-confirm-reset="${a.id}">${compact ? '' : icon('check', 'sm')}确认已重置</button>`
      : `<button class="btn sm" data-quick="${a.id}">${compact ? '' : icon('gauge', 'sm')}更新额度</button>`;
  return `${primary}<button class="btn sm ghost" data-edit="${a.id}">${compact ? '' : icon('edit', 'sm')}编辑</button>`;
}

function cardHTML(a) {
  const now = Date.now();
  return `<article class="card acct s-${a.status} ${a.recommended ? 'recommended' : ''}" data-id="${a.id}">
    <div class="head"><div class="who">${provHTML(a)}${sharedHTML(a)}${tagHTML(a)}</div>${pillHTML(a)}</div>
    <div class="name">${esc(a.name)}</div>
    <div class="login">${esc(a.account)}<button class="icon-btn" data-copy="${esc(a.account)}" title="复制账号">${icon('copy', 'sm')}</button></div>
    <div>
      <div class="meter-row">
        <span class="big"><span class="pct">${a.usedEff}%</span><small>已用${a.inferredReset ? '（推断）' : ''}</small></span>
        <span class="right">${a.inferredReset ? `记录值 ${a.used}%` : (a.updated ? '记录于 ' + fmtRel(a.updated) : '')}</span>
      </div>
      <div class="meter" ${a.expired ? '' : `data-drag="${a.id}" title="拖动或点击修改已用额度"`}><i style="width:${a.usedEff}%"></i></div>
    </div>
    <div class="meta">${icon('refresh', 'sm')}每${fmtReset(a)} 重置<span class="spacer"></span><span class="${a.expired ? 'faint' : ''}">${a.expired ? '已到期，不再重置' : fmtCountdown(a.next - now)}</span></div>
    <div class="meta">${icon('calendar', 'sm')}${subLine(a)}</div>
    ${a.notes ? `<div class="meta notes" title="${esc(a.notes)}">${icon('note', 'sm')}<span>${esc(a.notes)}</span></div>` : ''}
    ${a.inferredReset ? `<div class="note">${icon('info', 'sm')}<span>上次记录（${fmtRel(a.updated)}）早于最近一次重置 ${fmtDT(a.last)}，已按 0% 显示。确认后将已用额度记为 0%。</span></div>` : ''}
    <div class="creds">${pwHTML(a)}${chipsHTML(a)}</div>
    <div class="actions">${actionsHTML(a)}</div>
  </article>`;
}
function boardHTML(list) {
  if (filterOwner) return `<div class="grid">${list.map(cardHTML).join('')}</div>`;   // 已选定用户：直接平铺
  return groupByOwner(list).map(([k, g]) => { const s = groupStats(g); return `<section class="group">
    <header class="group-head"><span class="group-title">${groupIcon(k)}${esc(k)}</span><span class="group-count">${g.length}</span><span class="group-sum">可用 ${s.avail}/${s.act} · 平均已用 ${s.avg}%${s.expired ? ` · 已到期 ${s.expired}` : ''}</span></header>
    <div class="grid">${g.map(cardHTML).join('')}</div></section>`; }).join('');
}
function tableHTML(list) {
  const now = Date.now();
  const row = a => `<tr class="s-${a.status} ${a.recommended ? 'recommended' : ''}" data-id="${a.id}">
      <td class="strong">${esc(a.name)}${tagHTML(a)}</td>
      <td>${provHTML(a)}${sharedHTML(a)}</td>
      <td class="mono">${esc(a.account)}<button class="icon-btn" data-copy="${esc(a.account)}" title="复制账号">${icon('copy', 'sm')}</button></td>
      <td class="num"><span class="mini"><span class="meter" ${a.expired ? '' : `data-drag="${a.id}" title="拖动或点击修改已用额度"`}><i style="width:${a.usedEff}%"></i></span><b class="pct">${a.usedEff}%</b></span></td>
      <td>${pillHTML(a)}</td>
      <td>${fmtReset(a)}</td>
      <td class="num">${a.expired ? '<span class="muted">—</span>' : fmtCountdown(a.next - now)}</td>
      <td class="num">${a.subEnd ? fmtDT(a.subEnd) + (a.expired ? ' <span style="color:var(--crit);font-weight:600">已到期</span>' : ` <span class="muted">${a.daysLeft} 天后</span>`) : '—'}</td>
      <td class="mono">${pwHTML(a)}</td>
      <td>${chipsHTML(a, true) || '<span class="muted">—</span>'}</td>
      <td class="notes" title="${esc(a.notes)}">${esc(a.notes) || '<span class="muted">—</span>'}</td>
      <td>${actionsHTML(a, true)}</td>
    </tr>`;
  const body = filterOwner
    ? list.map(row).join('')
    : groupByOwner(list).map(([k, g]) => `<tr class="group"><td colspan="12">${groupIcon(k)}${esc(k)} <span class="muted">${g.length} 个账号</span></td></tr>${g.map(row).join('')}`).join('');
  return `<div class="card table-wrap"><table class="list">
    <thead><tr><th>用户名</th><th>服务商</th><th>账号</th><th>已用额度</th><th>状态</th><th>重置时间</th><th>下次重置</th><th>订阅到期</th><th>密码</th><th>附加</th><th>备注</th><th></th></tr></thead>
    <tbody>${body}</tbody></table></div>`;
}

function renderFilters() {
  const owners = [...new Set(accounts.map(ownerOf).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'));
  const provs = [...new Set(accounts.map(a => a.provider).filter(Boolean))].sort();
  if (accounts.length) {   // 数据还没加载时不要动筛选，否则刷新后记住的用户会被清掉
    if (filterOwner && !owners.includes(filterOwner)) { filterOwner = ''; syncUrl(); }
    if (filterProvider && !provs.includes(filterProvider)) { filterProvider = ''; syncUrl(); }
  }
  document.getElementById('ownerFilter').innerHTML = `<option value="">全部</option>` + owners.map(o => `<option value="${esc(o)}" ${o === filterOwner ? 'selected' : ''}>${esc(o)}</option>`).join('');
  document.getElementById('provFilter').innerHTML = `<option value="">全部</option>` + provs.map(p => `<option value="${esc(p)}" ${p === filterProvider ? 'selected' : ''}>${esc(p)}</option>`).join('');
  document.getElementById('owners').innerHTML = [SHARED, ...owners].map(o => `<option value="${esc(o)}">`).join('');
}
function renderFooter() {
  document.getElementById('logoutForm').hidden = !(health && health.authEnabled);
}
function render() {
  if (drag) return;                 // 正在拖动进度条时不要重绘，松手后由保存触发
  refreshProviderOrder();
  renderFilters();
  const list = sortedList();
  renderOverview(list);
  renderTimeline(list);
  const groups = groupByOwner(list);
  document.getElementById('countLabel').textContent = filterOwner ? `${list.length} 个 · ${filterOwner}` : `${list.length} 个 · ${groups.length} 个用户标签`;
  renderFooter();
  const host = document.getElementById('accounts');
  if (!list.length) {
    host.innerHTML = `<div class="card" style="padding:40px;text-align:center;color:var(--ink-3)">${accounts.length ? '当前筛选下没有账号' : '还没有账号，点右上角「新增账号」开始'}</div>`;
    return;
  }
  host.innerHTML = view === 'cards' ? boardHTML(list) : tableHTML(list);
}

/* ===================== 交互 ===================== */
let toastTimer;
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 1800);
}
function legacyCopy(text) {
  // navigator.clipboard 只在 HTTPS / localhost 可用；局域网明文 HTTP 下用传统办法：临时文本框选中后 execCommand('copy')
  const ta = document.createElement('textarea');
  ta.value = text; ta.setAttribute('readonly', '');
  ta.style.cssText = 'position:fixed;top:-1000px;left:0;opacity:0';
  document.body.appendChild(ta);
  ta.select(); ta.setSelectionRange(0, text.length);
  let ok = false;
  try { ok = document.execCommand('copy'); } catch { ok = false; }
  document.body.removeChild(ta);
  return ok;
}
function copyText(text) {
  const done = () => toast('已复制');
  const fail = () => toast('复制失败，请手动选择');
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(done, () => (legacyCopy(text) ? done() : fail()));
  } else {
    legacyCopy(text) ? done() : fail();
  }
}
function busy(btn, on) { if (btn) { btn.disabled = on; btn.style.opacity = on ? .6 : ''; } }

const editor = document.getElementById('editor'), editorForm = document.getElementById('editorForm');
const quick = document.getElementById('quick'), quickForm = document.getElementById('quickForm');

function openEditor(id, opts = {}) {
  const a = id ? accounts.find(x => x.id === id) : null;
  const f = editorForm.elements;
  editorForm.reset();
  document.getElementById('editorTitle').textContent = a ? (opts.renew ? `续订 · ${a.name}` : `编辑账号 · ${a.name}`) : '新增账号';
  f.owner.value = a ? (ownerOf(a) || SHARED) : (filterOwner || SHARED);   // 新增时默认「全部」，正在筛选某个用户则默认该用户
  f.name.value = a?.name || ''; f.provider.value = a?.provider || ''; f.account.value = a?.account || ''; f.password.value = a?.password || '';
  f.resetDay.value = a?.resetDay || 1; f.resetTime.value = a?.resetTime || '08:00';
  f.subStart.value = opts.renew || !a?.subStart ? nowLocalStr() : toLocalInput(a.subStart);
  f.used.value = f.usedRange.value = a && !opts.renew ? a.used : 0;
  f.notes.value = a?.notes || '';
  f.mailPlatform.value = a?.mailPlatform || ''; f.recoveryEmail.value = a?.recoveryEmail || ''; f.phone.value = a?.phone || ''; f.smsPlatform.value = a?.smsPlatform || ''; f.totp.value = a?.totp || '';
  f.password.type = 'password';
  document.getElementById('optional').open = !!(a && (a.mailPlatform || a.recoveryEmail || a.phone || a.smsPlatform || a.totp));
  document.getElementById('editorDelete').hidden = !a;
  editorForm.dataset.id = a ? a.id : '';
  editor.showModal();
  if (opts.renew) f.subStart.focus();
}
editorForm.addEventListener('submit', async e => {
  e.preventDefault();
  if (!editorForm.reportValidity()) return;
  const f = editorForm.elements;
  const data = {
    owner: normalizeOwner(f.owner.value), name: f.name.value.trim(), provider: f.provider.value.trim(), account: f.account.value.trim(), password: f.password.value,
    resetDay: +f.resetDay.value, resetTime: f.resetTime.value, subStart: f.subStart.value,
    used: Math.min(100, Math.max(0, +f.used.value || 0)), notes: f.notes.value.trim(),
    mailPlatform: f.mailPlatform.value.trim(), recoveryEmail: f.recoveryEmail.value.trim(), phone: f.phone.value.trim(), smsPlatform: f.smsPlatform.value.trim(), totp: f.totp.value.trim(),
  };
  const id = +editorForm.dataset.id;
  const old = id ? accounts.find(x => x.id === id) : null;
  if (old && old.used === data.used) delete data.used;      // 没改已用额度就不提交，避免刷新记录时间
  const btn = editorForm.querySelector('button[type=submit]');
  busy(btn, true);
  try {
    await saveAccount(id, data);
    editor.close(); toast('已保存');
  } catch (err) {
    toast(`保存失败：${err.message}`);
  } finally { busy(btn, false); }
});
document.getElementById('editorDelete').addEventListener('click', async () => {
  const id = +editorForm.dataset.id;
  const a = accounts.find(x => x.id === id);
  if (!a || !confirm(`删除账号「${a.name}」？此操作不可恢复。`)) return;
  try { await deleteAccount(id); editor.close(); toast('已删除'); }
  catch (err) { toast(`删除失败：${err.message}`); }
});
editorForm.querySelector('[data-eye]').addEventListener('click', () => {
  const p = editorForm.elements.password; p.type = p.type === 'password' ? 'text' : 'password';
});
for (const form of [editorForm, quickForm]) {           // 滑块与数字联动
  const r = form.elements.usedRange, n = form.elements.used;
  const sync = v => { r.value = n.value = v; if (form === quickForm) document.getElementById('quickValue').textContent = v; };
  r.addEventListener('input', () => sync(r.value));
  n.addEventListener('input', () => sync(Math.min(100, Math.max(0, +n.value || 0))));
}

function openQuick(id) {
  const a = accounts.find(x => x.id === id);
  if (!a) return;
  document.getElementById('quickTitle').textContent = `更新已用额度 · ${a.name}`;
  quickForm.elements.used.value = quickForm.elements.usedRange.value = a.used;
  document.getElementById('quickValue').textContent = a.used;
  quickForm.dataset.id = id;
  quick.showModal();
}
async function applyUsed(id, used, msg) {
  try { await setUsed(id, used); toast(msg); }
  catch (err) { toast(`更新失败：${err.message}`); }
}
quickForm.addEventListener('submit', e => {
  e.preventDefault();
  quick.close();
  applyUsed(+quickForm.dataset.id, Math.min(100, Math.max(0, +quickForm.elements.used.value || 0)), '额度已更新');
});
document.getElementById('quickZero').addEventListener('click', () => {
  quick.close();
  applyUsed(+quickForm.dataset.id, 0, '已记为 0%');
});

document.addEventListener('click', e => {
  const t = e.target.closest('[data-copy],[data-toggle-pw],[data-quick],[data-edit],[data-renew],[data-confirm-reset],[data-goto],[data-close],[data-tl]');
  if (!t) return;
  if (t.dataset.copy != null)     return copyText(t.dataset.copy);
  if (t.dataset.togglePw)         { const id = +t.dataset.togglePw; revealed.has(id) ? revealed.delete(id) : revealed.add(id); return render(); }
  if (t.dataset.quick)            return openQuick(+t.dataset.quick);
  if (t.dataset.edit)             return openEditor(+t.dataset.edit);
  if (t.dataset.renew)            return openEditor(+t.dataset.renew, { renew: true });
  if (t.dataset.confirmReset)     return applyUsed(+t.dataset.confirmReset, 0, '已确认重置，记为 0%');
  if (t.dataset.close)            return document.getElementById(t.dataset.close).close();
  if (t.dataset.tl) {
    const scroller = document.querySelector('.tl-scroll');
    if (!scroller) return;
    if (t.dataset.tl === 'now') { scroller.scrollTo({ left: 0, behavior: 'auto' }); return; }   // 时间轴从今天 0 点起画，「现在」一定在第一天里：回到起点即可
    const i = SCALES.indexOf(TL.scale), ni = Math.min(SCALES.length - 1, Math.max(0, i + (t.dataset.tl === 'zoom+' ? 1 : -1)));
    if (ni === i) return;
    const leftDays = scroller.scrollLeft / TL.scale;          // 保持左边缘对应的时刻不变
    TL.scale = SCALES[ni]; TL.pendingScroll = leftDays * TL.scale;
    return render();
  }
  if (t.dataset.goto) {
    const el = document.querySelector(`.acct[data-id="${t.dataset.goto}"], tr[data-id="${t.dataset.goto}"]`);
    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 1200); }
  }
});
// 进度条拖动 / 点击直接改已用额度：拖动时实时显示，松手后保存
let drag = null;
function dragValue(d, clientX) { return Math.max(0, Math.min(100, Math.round((clientX - d.rect.left) / d.rect.width * 100))); }
function dragApply(d, v) {
  d.value = v;
  d.fill.style.width = v + '%';
  if (d.pct) d.pct.textContent = v + '%';
}
document.addEventListener('pointerdown', e => {
  const m = e.target.closest('.meter[data-drag]');
  if (!m || e.button !== 0) return;
  e.preventDefault();
  const id = +m.dataset.drag;
  const host = m.closest('.acct, tr');
  drag = { id, m, fill: m.querySelector('i'), pct: host ? host.querySelector('.pct') : null, rect: m.getBoundingClientRect(),
           start: (accounts.find(a => a.id === id) || {}).used, value: 0 };
  m.classList.add('dragging');
  try { m.setPointerCapture(e.pointerId); } catch { /* ignore */ }
  dragApply(drag, dragValue(drag, e.clientX));
});
document.addEventListener('pointermove', e => { if (drag) dragApply(drag, dragValue(drag, e.clientX)); });
async function dragEnd(e, cancelled) {
  if (!drag) return;
  const d = drag; drag = null;
  d.m.classList.remove('dragging');
  try { d.m.releasePointerCapture(e.pointerId); } catch { /* ignore */ }
  if (cancelled || d.value === d.start) return render();
  await applyUsed(d.id, d.value, `已用额度改为 ${d.value}%`);
}
document.addEventListener('pointerup', e => dragEnd(e, false));
document.addEventListener('pointercancel', e => dragEnd(e, true));

// 时间线十字线：鼠标悬停显示该时刻
const tlHost = document.getElementById('timeline');
function hideXh() { const g = tlHost.querySelector('.xh-g'); if (g) g.style.display = 'none'; }
tlHost.addEventListener('mousemove', e => {
  const svg = tlHost.querySelector('.tl-inner > svg'); const g = tlHost.querySelector('.xh-g');
  if (!svg || !g || e.target.closest('.tl-labels') || e.target.closest('.tl-head')) return hideXh();
  const px = e.clientX - svg.getBoundingClientRect().left;
  if (px < 0 || px > TL.W) return hideXh();
  const t = new Date(TL.start.getTime() + px / TL.scale * D);
  t.setMinutes(Math.round(t.getMinutes() / 10) * 10, 0, 0);
  g.style.display = '';
  g.querySelector('line').setAttribute('x1', px); g.querySelector('line').setAttribute('x2', px);
  const chip = g.querySelector('.xh-chip'); const text = chip.querySelector('text');
  text.textContent = `${DAYS[(t.getDay() + 6) % 7]} ${fmtDate(t)} ${pad(t.getHours())}:${pad(t.getMinutes())}`;
  const w = Math.ceil(text.getBBox().width) + 12; chip.querySelector('rect').setAttribute('width', w);
  const cx = px + 8 + w > TL.W ? px - 8 - w : px + 8;
  chip.setAttribute('transform', `translate(${cx}, 23)`);
});
tlHost.addEventListener('mouseleave', hideXh);

document.getElementById('addBtn').addEventListener('click', () => openEditor(null));
document.getElementById('sort').addEventListener('change', e => { sortBy = e.target.value; savePrefs(); render(); });
document.getElementById('provFilter').addEventListener('change', e => { filterProvider = e.target.value; savePrefs(); render(); });
document.getElementById('ownerFilter').addEventListener('change', e => { filterOwner = e.target.value; savePrefs(); render(); });
function applyViewButtons() {
  document.querySelectorAll('#viewSwitch button').forEach(x => x.classList.toggle('active', x.dataset.view === view));
}
document.getElementById('viewSwitch').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  view = b.dataset.view;
  applyViewButtons(); savePrefs();
  render();
});
loadPrefs();
document.getElementById('sort').value = sortBy;
applyViewButtons();
syncUrl();

// 深浅色切换（跟随系统，可手动覆盖并记住）
const themeBtn = document.getElementById('themeBtn');
const isDark = () => { const t = document.documentElement.dataset.theme; return t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; };
function applyTheme(t) { if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; themeBtn.innerHTML = icon(isDark() ? 'sun' : 'moon'); }
themeBtn.addEventListener('click', () => { const next = isDark() ? 'light' : 'dark'; try { localStorage.setItem('theme', next); } catch { /* 私密模式等 */ } applyTheme(next); });
let savedTheme = null; try { savedTheme = localStorage.getItem('theme'); } catch { /* ignore */ }
applyTheme(savedTheme);

render();                       // 先画空壳，避免闪烁
load();
setInterval(load, 60000);       // 每分钟重新拉取（多端修改保持一致）并刷新倒计时
document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
