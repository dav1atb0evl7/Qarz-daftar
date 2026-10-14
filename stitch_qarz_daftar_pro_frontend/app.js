/**
 * Qarz Daftar Pro - Enterprise Ledger Frontend Application
 * Interacts with Django REST Framework backend API
 */

const API_BASE = (() => {
  if (window.location.port === '8000') return '/api/v1';
  const host = window.location.hostname || '127.0.0.1';
  return `http://${host}:8000/api/v1`;
})();

// Global Application State
const state = {
  token: localStorage.getItem('qarz_access_token') || '',
  refreshToken: localStorage.getItem('qarz_refresh_token') || '',
  user: null,
  shops: [],
  activeShop: (() => {
    try {
      const saved = localStorage.getItem('qarz_active_shop');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  })(),
  customers: [],
  debts: [],
  payments: [],
  summary: null,
  activeTab: 'boshqaruv-paneli',
  isOnline: false,
};

// ==========================================
// API HELPER WITH AUTO-AUTH & TOKEN REFRESH
// ==========================================
async function apiRequest(endpoint, options = {}) {
  if (!state.token && !endpoint.includes('/auth/')) {
    document.body.classList.add('unauthenticated');
    showAuthModal('login');
    throw new Error("Iltimos, avval tizimga kiring.");
  }

  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(state.token ? { 'Authorization': `Bearer ${state.token}` } : {}),
    ...(state.activeShop ? { 'X-Shop-ID': state.activeShop.id } : {}),
    ...(options.headers || {})
  };

  try {
    const res = await fetch(url, { ...options, headers });
    
    // Auto-refresh token if 401
    if (res.status === 401 && !endpoint.includes('/auth/')) {
      if (state.refreshToken) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
          headers['Authorization'] = `Bearer ${state.token}`;
          const retryRes = await fetch(url, { ...options, headers });
          return handleApiResponse(retryRes);
        }
      }
      handleLogout();
      throw new Error("Sessiya muddati tugadi. Iltimos, qayta kiring.");
    }

    return await handleApiResponse(res);
  } catch (err) {
    console.warn(`API Connection warning (${endpoint}):`, err);
    state.isOnline = false;
    updateServerStatusBadge();
    throw err;
  }
}

async function handleApiResponse(res) {
  if (res.status === 204) return { success: true };
  const contentType = res.headers.get('content-type') || '';
  
  if (contentType.includes('text/csv') || contentType.includes('spreadsheetml') || contentType.includes('pdf')) {
    return res.blob();
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorMsg = data?.error?.message || data?.detail || `Xatolik yuz berdi (${res.status})`;
    throw new Error(errorMsg);
  }
  return data;
}

async function refreshAccessToken() {
  try {
    const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: state.refreshToken })
    });
    if (res.ok) {
      const data = await res.json();
      state.token = data.access;
      localStorage.setItem('qarz_access_token', data.access);
      return true;
    }
  } catch (e) {
    console.error('Refresh token error:', e);
  }
  return false;
}

// ==========================================
// INITIALIZATION & AUTHENTICATION
// ==========================================
async function initApp() {
  updateServerStatusBadge();
  setupNavigation();
  setupModalListeners();

  if (!state.token) {
    document.body.classList.add('unauthenticated');
    showAuthModal('login');
    return;
  }

  try {
    await fetchUserProfile();
    await fetchShops();

    document.body.classList.remove('unauthenticated');
    state.isOnline = true;
    updateServerStatusBadge();

    if (state.shops.length === 0) {
      showToast("Do'kon mavjud emas. Iltimos, birinchi do'koningizni yarating.", "info");
      openModal('modal-new-shop');
    } else {
      await refreshCurrentView();
    }
  } catch (err) {
    console.warn("Auth or profile fetch error:", err);
    state.isOnline = false;
    updateServerStatusBadge();
    handleLogout();
  }
}

function showAuthModal(tab = 'login') {
  switchAuthTab(tab);
  openModal('modal-auth');
}

function closeAuthModal() {
  closeModal('modal-auth');
}

function switchAuthTab(tab) {
  const btnLogin = document.getElementById('tab-btn-login');
  const btnReg = document.getElementById('tab-btn-register');
  const formLogin = document.getElementById('form-login');
  const formReg = document.getElementById('form-register');
  const formForgot = document.getElementById('form-forgot');
  const adminHint = document.getElementById('auth-admin-hint');

  // Clear any existing alert messages
  const loginErr = document.getElementById('login-error-alert');
  const regErr = document.getElementById('register-error-alert');
  const regSuccess = document.getElementById('register-success-alert');
  if (loginErr) loginErr.classList.add('hidden');
  if (regErr) regErr.classList.add('hidden');
  if (regSuccess) regSuccess.classList.add('hidden');

  if (tab === 'login') {
    if (btnLogin) btnLogin.className = "flex-1 py-2 text-xs font-bold rounded-lg transition-all bg-white text-slate-900 shadow-sm";
    if (btnReg) btnReg.className = "flex-1 py-2 text-xs font-bold rounded-lg transition-all text-slate-500 hover:text-slate-900";
    if (formLogin) formLogin.classList.remove('hidden');
    if (formReg) formReg.classList.add('hidden');
    if (formForgot) formForgot.classList.add('hidden');
    if (adminHint) adminHint.classList.remove('hidden');
  } else if (tab === 'register') {
    if (btnReg) btnReg.className = "flex-1 py-2 text-xs font-bold rounded-lg transition-all bg-white text-slate-900 shadow-sm";
    if (btnLogin) btnLogin.className = "flex-1 py-2 text-xs font-bold rounded-lg transition-all text-slate-500 hover:text-slate-900";
    if (formReg) formReg.classList.remove('hidden');
    if (formLogin) formLogin.classList.add('hidden');
    if (formForgot) formForgot.classList.add('hidden');
    if (adminHint) adminHint.classList.add('hidden');
  } else if (tab === 'forgot') {
    if (btnLogin) btnLogin.className = "flex-1 py-2 text-xs font-bold rounded-lg transition-all text-slate-500 hover:text-slate-900";
    if (btnReg) btnReg.className = "flex-1 py-2 text-xs font-bold rounded-lg transition-all text-slate-500 hover:text-slate-900";
    if (formForgot) formForgot.classList.remove('hidden');
    if (formLogin) formLogin.classList.add('hidden');
    if (formReg) formReg.classList.add('hidden');
    if (adminHint) adminHint.classList.add('hidden');
  }
}

async function handleLoginSubmit(e) {
  if (e && e.preventDefault) e.preventDefault();
  const alertEl = document.getElementById('login-error-alert');
  const alertText = document.getElementById('login-error-text');
  const submitBtn = document.getElementById('btn-login-submit');
  if (alertEl) alertEl.classList.add('hidden');

  const emailEl = document.getElementById('login-email');
  const passwordEl = document.getElementById('login-password');
  const email = emailEl ? emailEl.value.trim() : '';
  const password = passwordEl ? passwordEl.value : '';

  if (!email || !password) {
    if (alertText) alertText.textContent = "Email va parolni kiriting.";
    if (alertEl) alertEl.classList.remove('hidden');
    return;
  }

  const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-sm animate-spin">sync</span> Tekshirilmoqda...`;
  }

  try {
    const res = await apiRequest('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    const payload = res?.data || res || {};
    const access = payload.access || payload.tokens?.access || res?.access;
    const refresh = payload.refresh || payload.tokens?.refresh || res?.refresh;
    const user = payload.user || res?.user;

    if (!access) throw new Error("Avtorizatsiya tokeni olinmadi.");

    state.token = access;
    state.refreshToken = refresh;
    state.user = user;
    state.isOnline = true;
    localStorage.setItem('qarz_access_token', state.token);
    localStorage.setItem('qarz_refresh_token', state.refreshToken);

    updateUserHeaderUI();
    updateServerStatusBadge();
    document.body.classList.remove('unauthenticated');
    closeModal('modal-auth');
    showToast("Tizimga muvaffaqiyatli kirdingiz!", 'success');

    await fetchShops();
    if (state.shops.length === 0) {
      openModal('modal-new-shop');
    } else {
      await refreshCurrentView();
    }
  } catch (err) {
    const msg = err.message || "Kirishda xatolik yuz berdi.";
    if (alertText) alertText.textContent = msg;
    if (alertEl) alertEl.classList.remove('hidden');
    showToast(msg, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnHtml;
    }
  }
}

async function handleRegisterSubmit(e) {
  if (e && e.preventDefault) e.preventDefault();
  
  const alertEl = document.getElementById('register-error-alert');
  const alertText = document.getElementById('register-error-text');
  const successEl = document.getElementById('register-success-alert');
  const successText = document.getElementById('register-success-text');
  const submitBtn = document.getElementById('btn-register-submit') || document.querySelector('#form-register button[type="submit"]');

  if (alertEl) alertEl.classList.add('hidden');
  if (successEl) successEl.classList.add('hidden');

  const fullNameEl = document.getElementById('reg-name');
  const phoneEl = document.getElementById('reg-phone');
  const emailEl = document.getElementById('reg-email');
  const passEl = document.getElementById('reg-password');
  const passConfirmEl = document.getElementById('reg-password-confirm');

  const fullName = fullNameEl ? fullNameEl.value.trim() : '';
  const phone = phoneEl ? phoneEl.value.trim() : '';
  const email = emailEl ? emailEl.value.trim() : '';
  const password = passEl ? passEl.value : '';
  const passwordConfirm = passConfirmEl ? passConfirmEl.value : '';

  if (!email || !password) {
    const msg = "Iltimos, elektron pochta va parolni kiriting!";
    if (alertText) alertText.textContent = msg;
    if (alertEl) alertEl.classList.remove('hidden');
    showToast(msg, 'error');
    return;
  }

  if (password.length < 8) {
    const msg = "Parol kamida 8 ta belgidan iborat bo'lishi kerak!";
    if (alertText) alertText.textContent = msg;
    if (alertEl) alertEl.classList.remove('hidden');
    showToast(msg, 'error');
    return;
  }

  if (password !== passwordConfirm) {
    const msg = "Kiritilgan parollar bir-biriga mos kelmadi!";
    if (alertText) alertText.textContent = msg;
    if (alertEl) alertEl.classList.remove('hidden');
    showToast(msg, 'error');
    return;
  }

  const origBtnHtml = submitBtn ? submitBtn.innerHTML : '';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="material-symbols-outlined text-sm animate-spin">sync</span> Ro'yxatdan o'tkazilmoqda...`;
  }

  try {
    const res = await apiRequest('/auth/register/', {
      method: 'POST',
      body: JSON.stringify({
        email,
        full_name: fullName,
        phone_number: phone,
        password,
        password_confirm: passwordConfirm,
        role: 'SHOP_OWNER'
      })
    });

    const payload = res?.data || res || {};
    const access = payload.access || res?.tokens?.access || res?.access;
    const refresh = payload.refresh || res?.tokens?.refresh || res?.refresh;
    const user = payload.user || payload;

    if (access) {
      // Immediate auto-login into system
      state.token = access;
      state.refreshToken = refresh;
      state.user = user;
      state.isOnline = true;
      localStorage.setItem('qarz_access_token', state.token);
      localStorage.setItem('qarz_refresh_token', state.refreshToken);

      updateUserHeaderUI();
      updateServerStatusBadge();
      document.body.classList.remove('unauthenticated');
      closeModal('modal-auth');
      showToast("Muvaffaqiyatli ro'yxatdan o'tdingiz!", 'success');

      await fetchShops();
      if (state.shops.length === 0) {
        openModal('modal-new-shop');
      } else {
        await refreshCurrentView();
      }
    } else {
      // Fallback: auto-login via /auth/login/
      try {
        const loginRes = await apiRequest('/auth/login/', {
          method: 'POST',
          body: JSON.stringify({ email, password })
        });
        const lPayload = loginRes?.data || loginRes || {};
        const lAccess = lPayload.access || loginRes?.access;
        const lRefresh = lPayload.refresh || loginRes?.refresh;
        const lUser = lPayload.user || loginRes?.user;

        if (lAccess) {
          state.token = lAccess;
          state.refreshToken = lRefresh;
          state.user = lUser;
          state.isOnline = true;
          localStorage.setItem('qarz_access_token', state.token);
          localStorage.setItem('qarz_refresh_token', state.refreshToken);

          updateUserHeaderUI();
          updateServerStatusBadge();
          document.body.classList.remove('unauthenticated');
          closeModal('modal-auth');
          showToast("Muvaffaqiyatli ro'yxatdan o'tdingiz!", 'success');

          await fetchShops();
          if (state.shops.length === 0) {
            openModal('modal-new-shop');
          } else {
            await refreshCurrentView();
          }
          return;
        }
      } catch (loginErr) {
        console.warn("Auto-login fallback:", loginErr);
      }

      // If auto-login fails, redirect to login tab with credentials
      showToast("Akkaunt yaratildi! Endi tizimga kirishingiz mumkin.", 'success');
      const loginEmailInput = document.getElementById('login-email');
      const loginPassInput = document.getElementById('login-password');
      if (loginEmailInput) loginEmailInput.value = email;
      if (loginPassInput) loginPassInput.value = password;
      switchAuthTab('login');
    }
  } catch (err) {
    let msg = err.message || "Ro'yxatdan o'tishda xatolik yuz berdi.";
    if (msg.includes("already exists") || msg.includes("mavjud")) {
      msg = "Ushbu email manziliga ega foydalanuvchi allaqachon ro'yxatdan o'tgan.";
    } else if (msg.includes("too common") || msg.includes("numeric")) {
      msg = "Parol juda oddiy. Iltimos, harf va raqamlar qatnashgan kuchliroq parol kiriting.";
    } else if (msg.includes("match")) {
      msg = "Parollar bir-biriga mos kelmadi.";
    }
    if (alertText) alertText.textContent = msg;
    if (alertEl) alertEl.classList.remove('hidden');
    showToast(msg, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = origBtnHtml;
    }
  }
}

async function handleForgotPasswordSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('forgot-email').value.trim();
  if (!email) {
    showToast("Email manzilini kiriting!", 'error');
    return;
  }

  const submitBtn = e.target.querySelector('button[type="submit"]');
  const origText = submitBtn ? submitBtn.innerHTML : '';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Yuborilmoqda...';
  }

  try {
    await apiRequest('/auth/password-reset/', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
    showToast("Agar ushbu email ro'yxatdan o'tgan bo'lsa, parolni tiklash havolasi yuborildi.", 'info');
    switchAuthTab('login');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = origText;
    }
  }
}

function handleLogout() {
  state.token = '';
  state.refreshToken = '';
  state.user = null;
  state.shops = [];
  state.activeShop = null;
  state.customers = [];
  state.debts = [];
  state.payments = [];
  state.summary = null;

  localStorage.removeItem('qarz_access_token');
  localStorage.removeItem('qarz_refresh_token');
  localStorage.removeItem('qarz_active_shop');

  updateUserHeaderUI();
  updateShopHeaderUI();
  renderDashboardUI();
  renderCustomersUI();
  renderDebtsUI();
  renderPaymentsUI();

  document.body.classList.add('unauthenticated');
  showToast("Tizimdan chiqildi", 'info');
  showAuthModal('login');
}

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isPass = input.type === 'password';
  input.type = isPass ? 'text' : 'password';

  // Toggle SVG eye icons if present
  if (btn) {
    const openEye = btn.querySelector('.eye-open');
    const closedEye = btn.querySelector('.eye-closed');
    if (openEye && closedEye) {
      openEye.classList.toggle('hidden', isPass);
      closedEye.classList.toggle('hidden', !isPass);
    }
    const icon = btn.querySelector('.material-symbols-outlined');
    if (icon) {
      icon.textContent = isPass ? 'visibility' : 'visibility_off';
    }
  }
}

async function handleCreateShopSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('shop-create-name').value.trim();
  const phone = document.getElementById('shop-create-phone').value.trim();
  const address = document.getElementById('shop-create-address').value.trim();
  const branchName = document.getElementById('shop-create-branch').value.trim() || 'Asosiy filial #01';
  const currency = document.getElementById('shop-create-currency').value || 'UZS';

  try {
    const res = await apiRequest('/shops/', {
      method: 'POST',
      body: JSON.stringify({
        name,
        phone_number: phone,
        address,
        main_branch_name: branchName,
        currency
      })
    });

    const newShop = res.data || res;
    showToast(`"${name}" do'koni muvaffaqiyatli yaratildi!`, 'success');
    closeModal('modal-new-shop');
    const formNewShop = document.getElementById('form-new-shop');
    if (formNewShop) formNewShop.reset();

    await fetchShops();
    if (newShop && newShop.id) {
      selectActiveShop(newShop.id);
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openShopSelectorModal() {
  const container = document.getElementById('shop-selector-list');
  if (!container) return;

  if (state.shops.length === 0) {
    container.innerHTML = `<div class="p-4 rounded-xl bg-slate-50 text-slate-500 text-xs text-center">Do'konlar mavjud emas. Yangi do'kon qo'shing.</div>`;
  } else {
    container.innerHTML = state.shops.map(s => `
      <div onclick="selectActiveShop('${s.id}')" class="p-3 rounded-xl border ${state.activeShop?.id === s.id ? 'border-blue-600 bg-blue-50/50' : 'border-slate-200 bg-white hover:border-slate-300'} flex items-center justify-between cursor-pointer transition-all">
        <div class="flex items-center gap-2.5">
          <span class="material-symbols-outlined text-blue-600">storefront</span>
          <div>
            <div class="text-xs font-bold text-slate-900">${escapeHtml(s.name)}</div>
            <div class="text-[11px] text-slate-500">${escapeHtml(s.branches?.[0]?.name || 'Asosiy filial')} • ${s.currency || 'UZS'}</div>
          </div>
        </div>
        ${state.activeShop?.id === s.id ? '<span class="material-symbols-outlined text-blue-600 text-lg">check_circle</span>' : ''}
      </div>
    `).join('');
  }

  openModal('modal-shop-selector');
}

function selectActiveShop(shopId) {
  const shop = state.shops.find(s => s.id === shopId);
  if (shop) {
    state.activeShop = shop;
    localStorage.setItem('qarz_active_shop', JSON.stringify(shop));
    updateShopHeaderUI();
    closeModal('modal-shop-selector');
    showToast(`Faol do'kon: ${shop.name}`, 'info');
    refreshCurrentView();
  }
}

async function fetchUserProfile() {
  try {
    const data = await apiRequest('/auth/me/');
    if (data.data) {
      state.user = data.data;
      updateUserHeaderUI();
    }
  } catch (e) {
    console.warn('Failed to fetch user profile:', e);
    throw e;
  }
}

async function fetchShops() {
  try {
    const data = await apiRequest('/shops/');
    state.shops = data.results || data.data || [];
    if (state.shops.length > 0) {
      if (!state.activeShop || !state.shops.some(s => s.id === state.activeShop.id)) {
        state.activeShop = state.shops[0];
      }
      localStorage.setItem('qarz_active_shop', JSON.stringify(state.activeShop));
      updateShopHeaderUI();
    } else {
      state.activeShop = null;
      localStorage.removeItem('qarz_active_shop');
      updateShopHeaderUI();
    }
  } catch (e) {
    console.warn('Failed to fetch shops:', e);
  }
}

function updateUserHeaderUI() {
  if (!state.user) {
    document.querySelectorAll('.user-name-display').forEach(el => el.textContent = 'Kirilmagan');
    document.querySelectorAll('.user-role-display').forEach(el => el.textContent = '-');
    const avatar = document.getElementById('user-avatar-initials');
    if (avatar) avatar.textContent = 'U';
    return;
  }
  const fullName = `${state.user.first_name || ''} ${state.user.last_name || ''}`.trim() || state.user.email;
  const roleName = state.user.role === 'SHOP_OWNER' ? 'Do\'kon Egasi' : (state.user.role === 'MANAGER' ? 'Boshqaruvchi' : (state.user.role === 'SUPER_ADMIN' ? 'Super Admin' : 'Kassir'));
  
  document.querySelectorAll('.user-name-display').forEach(el => el.textContent = fullName);
  document.querySelectorAll('.user-role-display').forEach(el => el.textContent = roleName);

  const initials = (state.user.first_name ? state.user.first_name.charAt(0) : (state.user.email ? state.user.email.charAt(0).toUpperCase() : 'U'));
  const avatar = document.getElementById('user-avatar-initials');
  if (avatar) avatar.textContent = initials;
}

function updateShopHeaderUI() {
  if (!state.activeShop) {
    document.querySelectorAll('.shop-name-display').forEach(el => el.textContent = "Do'kon tanlanmagan");
    document.querySelectorAll('.branch-name-display').forEach(el => el.textContent = "-");
    return;
  }
  document.querySelectorAll('.shop-name-display').forEach(el => el.textContent = state.activeShop.name);
  const branchName = state.activeShop.branches?.[0]?.name || 'Asosiy filial #01';
  document.querySelectorAll('.branch-name-display').forEach(el => el.textContent = branchName);
}

function updateServerStatusBadge() {
  const badge = document.getElementById('server-status-badge');
  if (!badge) return;
  if (state.isOnline) {
    badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span><span class="text-emerald-700 font-semibold text-xs">Django API: Jonli</span>`;
    badge.className = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200";
  } else {
    badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-500"></span><span class="text-amber-700 font-semibold text-xs">Mahalliy API kutilmoqda (port 8000)</span>`;
    badge.className = "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200";
  }
}

// ==========================================
// NAVIGATION & TABS
// ==========================================
function setupNavigation() {
  document.querySelectorAll('[data-path]').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const targetPath = link.getAttribute('data-path');
      switchTab(targetPath);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;

  // Update Sidebar active state
  document.querySelectorAll('[data-path]').forEach(link => {
    const isCurrent = link.getAttribute('data-path') === tabId;
    if (isCurrent) {
      link.className = "flex items-center justify-between px-3 py-2 rounded-xl transition-all group bg-blue-600 text-white shadow-sm font-semibold";
      const icon = link.querySelector('.material-symbols-outlined');
      if (icon) icon.className = "material-symbols-outlined text-lg text-white";
    } else {
      link.className = "flex items-center justify-between px-3 py-2 rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white transition-all group";
      const icon = link.querySelector('.material-symbols-outlined');
      if (icon) icon.className = "material-symbols-outlined text-lg text-slate-400 group-hover:text-white";
    }
  });

  // Switch views
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.remove('active');
  });

  const activePanel = document.getElementById(`view-${tabId}`);
  if (activePanel) {
    activePanel.classList.add('active');
  }

  // Load fresh data for this view
  refreshCurrentView();
}

async function refreshCurrentView() {
  switch (state.activeTab) {
    case 'boshqaruv-paneli':
      await loadDashboardData();
      break;
    case 'mijozlar':
      await loadCustomersData();
      break;
    case 'qarzlar':
      await loadDebtsData();
      break;
    case 'tolovlar':
      await loadPaymentsData();
      break;
    case 'hisobotlar':
      await loadReportsData();
      break;
    case 'telegram':
      await loadTelegramData();
      break;
    case 'sozlamalar':
      updateSettingsUI();
      break;
  }
}

// ==========================================
// 1. DASHBOARD VIEW (Boshqaruv paneli)
// ==========================================
async function loadDashboardData() {
  try {
    const [summaryRes, trendsRes, debtsAnalysisRes, debtsListRes] = await Promise.all([
      apiRequest('/reports/summary/').catch(() => null),
      apiRequest('/reports/payments/?interval=daily').catch(() => null),
      apiRequest('/reports/debts/').catch(() => null),
      apiRequest('/debts/?page_size=5').catch(() => null),
    ]);

    if (summaryRes?.data) state.summary = summaryRes.data;
    if (debtsListRes?.results) state.debts = debtsListRes.results;

    renderDashboardUI(summaryRes?.data, trendsRes?.data, debtsAnalysisRes?.data);
  } catch (e) {
    console.error("Dashboard data load error:", e);
  }
}

function renderDashboardUI(summary, trends, debtAnalysis) {
  const s = summary || state.summary || {
    current_outstanding_debt: "0.00",
    total_payments_collected: "0.00",
    total_overdue_debt: "0.00",
    total_customers_count: 0,
    active_debtors_count: 0,
    currency: "UZS"
  };

  const elTotalDebt = document.getElementById('kpi-total-debt');
  if (elTotalDebt) elTotalDebt.textContent = formatMoney(s.current_outstanding_debt);

  const elMonthCollected = document.getElementById('kpi-month-collected');
  if (elMonthCollected) elMonthCollected.textContent = formatMoney(s.total_payments_collected);

  const elOverdue = document.getElementById('kpi-overdue-debt');
  if (elOverdue) elOverdue.textContent = formatMoney(s.total_overdue_debt);

  const elTotalCustomers = document.getElementById('kpi-total-customers');
  if (elTotalCustomers) elTotalCustomers.textContent = s.total_customers_count;

  // Render recent transactions table
  renderRecentTransactions();

  // Render debt aging distribution if available
  if (debtAnalysis?.aging_distribution) {
    renderAgingDistribution(debtAnalysis.aging_distribution);
  }
}

function renderRecentTransactions() {
  const container = document.getElementById('recent-debts-table-body');
  if (!container) return;

  if (!state.debts || state.debts.length === 0) {
    container.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-400">Hozircha qarz yozuvlari yo'q</td></tr>`;
    return;
  }

  container.innerHTML = state.debts.slice(0, 5).map(debt => `
    <tr class="hover:bg-slate-50 border-b border-slate-100 transition-colors">
      <td class="py-3 px-4 font-semibold text-slate-900">${escapeHtml(debt.customer_name || 'Noma\'lum')}</td>
      <td class="py-3 px-4 text-slate-500 font-tabular">${debt.debt_date || '-'}</td>
      <td class="py-3 px-4 font-tabular text-slate-700">${debt.due_date || 'Belgilanmagan'}</td>
      <td class="py-3 px-4 text-right font-bold text-slate-900 font-tabular">${formatMoney(debt.amount)} <span class="text-xs text-slate-400">UZS</span></td>
      <td class="py-3 px-4 text-right font-bold ${parseFloat(debt.remaining_balance) > 0 ? 'text-red-600' : 'text-emerald-600'} font-tabular">${formatMoney(debt.remaining_balance)} <span class="text-xs text-slate-400">UZS</span></td>
      <td class="py-3 px-4 text-center">${getStatusBadge(debt.status)}</td>
    </tr>
  `).join('');
}

function renderAgingDistribution(aging) {
  const b1 = document.getElementById('aging-bar-0-30');
  const b2 = document.getElementById('aging-bar-31-60');
  const b3 = document.getElementById('aging-bar-61-90');
  const b4 = document.getElementById('aging-bar-90-plus');
  
  if (b1) document.getElementById('aging-val-0-30').textContent = formatMoney(aging['0_30_days'] || 0) + ' UZS';
  if (b2) document.getElementById('aging-val-31-60').textContent = formatMoney(aging['31_60_days'] || 0) + ' UZS';
  if (b3) document.getElementById('aging-val-61-90').textContent = formatMoney(aging['61_90_days'] || 0) + ' UZS';
  if (b4) document.getElementById('aging-val-90-plus').textContent = formatMoney(aging['90_plus_days'] || 0) + ' UZS';
}

// ==========================================
// 2. CUSTOMERS VIEW (Mijozlar)
// ==========================================
async function loadCustomersData() {
  try {
    const data = await apiRequest('/customers/');
    state.customers = data.results || data.data || [];
    renderCustomersUI();
  } catch (e) {
    console.error("Customers load error:", e);
  }
}

function renderCustomersUI() {
  const container = document.getElementById('customers-table-body');
  if (!container) return;

  const countBadge = document.getElementById('customers-count-badge');
  if (countBadge) countBadge.textContent = state.customers.length;

  if (state.customers.length === 0) {
    container.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">Mijozlar mavjud emas. Yangi mijoz qo'shing.</td></tr>`;
    return;
  }

  container.innerHTML = state.customers.map(c => `
    <tr class="hover:bg-slate-50 border-b border-slate-100 transition-colors">
      <td class="py-3.5 px-4">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center text-sm">
            ${escapeHtml(c.full_name?.charAt(0) || 'M')}
          </div>
          <div>
            <div class="font-semibold text-slate-900">${escapeHtml(c.full_name)}</div>
            <div class="text-xs text-slate-400">${c.notes || 'Doimiy mijoz'}</div>
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 font-tabular text-slate-700">${escapeHtml(c.phone_number)}</td>
      <td class="py-3.5 px-4 text-slate-500 text-sm">${escapeHtml(c.branch_name || 'Asosiy filial')}</td>
      <td class="py-3.5 px-4 text-right font-tabular text-slate-600">${formatMoney(c.credit_limit)} UZS</td>
      <td class="py-3.5 px-4 text-right font-tabular font-bold ${parseFloat(c.remaining_balance ?? c.total_outstanding_debt ?? 0) > 0 ? 'text-red-600' : 'text-emerald-600'}">
        ${formatMoney(c.remaining_balance ?? c.total_outstanding_debt ?? 0)} UZS
      </td>
      <td class="py-3.5 px-4 text-center">
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${c.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-600'}">
          ${c.status === 'ACTIVE' ? 'Faol' : 'Arxiv'}
        </span>
      </td>
      <td class="py-3.5 px-4 text-right">
        <div class="flex items-center justify-end gap-1.5">
          <button onclick="openNewDebtModal('${c.id}', '${escapeHtml(c.full_name)}')" class="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold transition-all">
            + Qarz
          </button>
        </div>
      </td>
    </tr>
  `).join('');
}

// Client-side search for customers
function filterCustomers(query) {
  const q = query.toLowerCase().trim();
  const rows = document.querySelectorAll('#customers-table-body tr');
  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(q) ? '' : 'none';
  });
}

// ==========================================
// 3. DEBTS VIEW (Qarzlar reyestri)
// ==========================================
async function loadDebtsData(statusFilter = '') {
  try {
    let endpoint = '/debts/';
    if (statusFilter && statusFilter !== 'ALL') {
      endpoint += `?status=${statusFilter}`;
    }
    const data = await apiRequest(endpoint);
    state.debts = data.results || data.data || [];
    renderDebtsUI();
  } catch (e) {
    console.error("Debts load error:", e);
  }
}

function renderDebtsUI() {
  const container = document.getElementById('debts-table-body');
  if (!container) return;

  const countBadge = document.getElementById('debts-count-badge');
  if (countBadge) countBadge.textContent = state.debts.length;

  if (state.debts.length === 0) {
    container.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-400">Qarz shartnomalari topilmadi.</td></tr>`;
    return;
  }

  container.innerHTML = state.debts.map(d => `
    <tr class="hover:bg-slate-50 border-b border-slate-100 transition-colors">
      <td class="py-3.5 px-4">
        <div class="font-semibold text-slate-900">${escapeHtml(d.customer_name || 'Mijoz')}</div>
        <div class="text-xs text-slate-500">${escapeHtml(d.description || 'Izohsiz')}</div>
      </td>
      <td class="py-3.5 px-4 font-tabular text-slate-600 text-sm">${d.debt_date || '-'}</td>
      <td class="py-3.5 px-4 font-tabular text-sm ${isPastDue(d.due_date, d.status) ? 'text-red-600 font-bold' : 'text-slate-600'}">
        ${d.due_date || 'Belgilanmagan'}
      </td>
      <td class="py-3.5 px-4 text-right font-bold text-slate-900 font-tabular">${formatMoney(d.amount)} UZS</td>
      <td class="py-3.5 px-4 text-right font-tabular text-emerald-600 font-semibold">${formatMoney(d.paid_amount)} UZS</td>
      <td class="py-3.5 px-4 text-right font-bold text-red-600 font-tabular">${formatMoney(d.remaining_balance)} UZS</td>
      <td class="py-3.5 px-4 text-center">${getStatusBadge(d.status)}</td>
      <td class="py-3.5 px-4 text-right">
        <div class="flex items-center justify-end gap-1.5">
          ${parseFloat(d.remaining_balance) > 0 ? `
            <button onclick="openPaymentModal('${d.id}', '${escapeHtml(d.customer_name)}', '${d.remaining_balance}')" class="px-2.5 py-1 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-semibold shadow-sm transition-all">
              To'lov
            </button>
          ` : ''}
          ${d.status !== 'CANCELLED' && parseFloat(d.paid_amount) === 0 ? `
            <button onclick="promptCancelDebt('${d.id}')" class="p-1 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 text-xs" title="Bekor qilish">
              <span class="material-symbols-outlined text-base">cancel</span>
            </button>
          ` : ''}
        </div>
      </td>
    </tr>
  `).join('');
}

// ==========================================
// 4. PAYMENTS & RECEIPT VIEW (To'lovlar)
// ==========================================
async function loadPaymentsData() {
  try {
    const data = await apiRequest('/payments/');
    state.payments = data.results || data.data || [];
    renderPaymentsUI();
  } catch (e) {
    console.error("Payments load error:", e);
  }
}

function renderPaymentsUI() {
  const container = document.getElementById('payments-table-body');
  if (!container) return;

  const countBadge = document.getElementById('payments-count-badge');
  if (countBadge) countBadge.textContent = state.payments.length;

  if (state.payments.length === 0) {
    container.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">To'lovlar tarixi mavjud emas.</td></tr>`;
    const receiptCard = document.getElementById('printable-receipt-card');
    if (receiptCard) {
      receiptCard.innerHTML = `<div class="p-8 text-center text-slate-400 text-xs">To'lovlar amalga oshirilgach, kvitansiya shu yerda ko'rinadi.</div>`;
    }
    return;
  }

  container.innerHTML = state.payments.map(p => `
    <tr class="hover:bg-slate-50 border-b border-slate-100 transition-colors">
      <td class="py-3.5 px-4">
        <span class="font-mono font-semibold text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700">${escapeHtml(p.receipt_number)}</span>
      </td>
      <td class="py-3.5 px-4 font-tabular text-slate-600 text-xs">${formatDateTime(p.payment_date)}</td>
      <td class="py-3.5 px-4 font-semibold text-slate-900">${escapeHtml(p.customer_name || 'Mijoz')}</td>
      <td class="py-3.5 px-4 text-center">
        <span class="px-2 py-0.5 rounded-full text-xs font-semibold ${getPaymentMethodBadge(p.payment_method)}">
          ${p.payment_method}
        </span>
      </td>
      <td class="py-3.5 px-4 text-right font-bold text-emerald-600 font-tabular">+${formatMoney(p.amount)} UZS</td>
      <td class="py-3.5 px-4 text-center">
        ${p.is_reversed ? '<span class="text-xs text-red-600 font-bold bg-red-50 px-2 py-0.5 rounded border border-red-200">Bekor qilingan</span>' : '<span class="text-xs text-emerald-600 font-semibold bg-emerald-50 px-2 py-0.5 rounded">Tasdiqlangan</span>'}
      </td>
      <td class="py-3.5 px-4 text-right">
        <div class="flex items-center justify-end gap-1.5">
          <button onclick="previewReceipt('${p.id}')" class="p-1 rounded-lg text-blue-600 hover:bg-blue-50 text-xs font-semibold" title="Chekni ko'rish">
            <span class="material-symbols-outlined text-base">receipt</span>
          </button>
          ${!p.is_reversed ? `
            <button onclick="promptReversePayment('${p.id}')" class="p-1 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 text-xs" title="To'lovni bekor qilish">
              <span class="material-symbols-outlined text-base">undo</span>
            </button>
          ` : ''}
        </div>
      </td>
    </tr>
  `).join('');

  // Auto-preview first payment on load
  if (state.payments.length > 0) {
    renderReceiptPreview(state.payments[0]);
  }
}

async function previewReceipt(paymentId) {
  try {
    const data = await apiRequest(`/payments/${paymentId}/receipt/`);
    if (data.receipt) {
      renderReceiptPreview(data.receipt);
    }
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function renderReceiptPreview(r) {
  const container = document.getElementById('printable-receipt-card');
  if (!container) return;

  const currentUserName = state.user ? `${state.user.first_name || ''} ${state.user.last_name || ''}`.trim() || state.user.email : 'Kassir';
  container.innerHTML = `
    <div id="printable-receipt-area" class="receipt-paper p-6 rounded-lg text-slate-800 text-sm max-w-sm mx-auto">
      <div class="text-center pb-4 border-b border-dashed border-slate-300">
        <div class="text-lg font-bold uppercase tracking-wider">${escapeHtml(r.shop_name || state.activeShop?.name || 'QARZ DAFTAR PRO')}</div>
        <div class="text-xs text-slate-500">${escapeHtml(r.branch_name || state.activeShop?.branches?.[0]?.name || 'Asosiy filial')}</div>
        <div class="text-xs text-slate-500">${escapeHtml(r.shop_address || state.activeShop?.address || '')}</div>
        <div class="text-xs text-slate-500">${escapeHtml(r.shop_phone || state.activeShop?.phone_number || '')}</div>
      </div>

      <div class="py-3 border-b border-dashed border-slate-300 text-xs space-y-1">
        <div class="flex justify-between"><span class="text-slate-500">Kvitansiya №:</span><span class="font-mono font-bold">${escapeHtml(r.receipt_number || '-')}</span></div>
        <div class="flex justify-between"><span class="text-slate-500">Sana:</span><span>${escapeHtml(r.payment_date || new Date().toLocaleString())}</span></div>
        <div class="flex justify-between"><span class="text-slate-500">Kassir:</span><span>${escapeHtml(r.cashier || currentUserName)}</span></div>
        <div class="flex justify-between"><span class="text-slate-500">Mijoz:</span><span class="font-bold">${escapeHtml(r.customer_name || '-')}</span></div>
      </div>

      <div class="py-4 border-b border-dashed border-slate-300 space-y-2">
        <div class="flex justify-between items-center text-base">
          <span class="font-bold">TO'LANDI:</span>
          <span class="font-bold text-emerald-600 text-lg">${escapeHtml(r.amount_paid || formatMoney(r.amount) + ' UZS')}</span>
        </div>
        <div class="text-xs text-slate-500 flex justify-between">
          <span>To'lov usuli:</span>
          <span class="font-semibold text-slate-700">${escapeHtml(r.payment_method || 'NAQD')}</span>
        </div>
        ${r.cash_portion ? `<div class="text-xs text-slate-400 flex justify-between"><span>Naqd qismi:</span><span>${r.cash_portion}</span></div>` : ''}
        ${r.card_portion ? `<div class="text-xs text-slate-400 flex justify-between"><span>Karta qismi:</span><span>${r.card_portion}</span></div>` : ''}
      </div>

      <div class="py-3 border-b border-dashed border-slate-300 text-xs space-y-1">
        <div class="flex justify-between font-semibold"><span class="text-slate-500">Qoldiq qarz:</span><span class="text-red-600 font-bold">${escapeHtml(r.remaining_debt || '0 UZS')}</span></div>
      </div>

      <div class="text-center pt-4 text-xs text-slate-400">
        <div>Xaridingiz uchun rahmat!</div>
        <div class="font-mono text-[10px] mt-1">FISKAL CHEK ID: ${escapeHtml(r.receipt_number || 'QD-RECEIPT')}</div>
      </div>
    </div>
  `;
}

// ==========================================
// 5. REPORTS & EXPORTS (Hisobotlar)
// ==========================================
async function loadReportsData() {
  try {
    const summary = await apiRequest('/reports/summary/');
    if (summary.data) {
      document.getElementById('rep-total-debt').textContent = formatMoney(summary.data.total_debt_created) + ' UZS';
      document.getElementById('rep-total-collected').textContent = formatMoney(summary.data.total_payments_collected) + ' UZS';
      document.getElementById('rep-cash-collected').textContent = formatMoney(summary.data.total_cash_collected) + ' UZS';
      document.getElementById('rep-card-collected').textContent = formatMoney(summary.data.total_card_collected) + ' UZS';
      document.getElementById('rep-reversed-amount').textContent = formatMoney(summary.data.total_reversed_amount) + ' UZS';
      document.getElementById('rep-current-debt').textContent = formatMoney(summary.data.current_outstanding_debt) + ' UZS';
      document.getElementById('rep-active-debtors').textContent = summary.data.active_debtors_count + ' nafar';
    }
  } catch (e) {
    console.error("Reports load error:", e);
  }
}

async function exportReport(type, format) {
  showToast(`${format.toUpperCase()} formatidagi hisobot yuklanmoqda...`, 'info');
  try {
    const blob = await apiRequest(`/reports/export/?type=${type}&format=${format}`);
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `qarz_daftar_${type}_${new Date().toISOString().slice(0, 10)}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast("Hisobot muvaffaqiyatli yuklab olindi!", 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

// ==========================================
// 6. TELEGRAM BOT INTEGRATION
// ==========================================
let linkCodeCountdownTimer = null;

async function loadTelegramData() {
  // If user already linked telegram
  if (state.user?.telegram_id) {
    const el = document.getElementById('telegram-linked-status');
    if (el) el.innerHTML = `
      <div class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 flex items-center gap-3">
        <span class="material-symbols-outlined text-2xl text-emerald-600">verified</span>
        <div>
          <div class="font-bold">Telegram akkaunt ulangan!</div>
          <div class="text-xs text-emerald-600">Telegram ID: ${state.user.telegram_id} (${state.user.telegram_username ? '@' + state.user.telegram_username : ''})</div>
        </div>
      </div>
    `;
  }
}

async function generateTelegramCode() {
  try {
    const data = await apiRequest('/telegram/link-code/', { method: 'POST' });
    if (data.code) {
      document.getElementById('telegram-code-display').textContent = data.code;
      startCodeCountdown(data.expires_in || 600);
      showToast("Yangi tasdiqlash kodi olindi!", 'success');
    }
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function startCodeCountdown(seconds) {
  clearInterval(linkCodeCountdownTimer);
  const timerEl = document.getElementById('telegram-code-timer');
  let remaining = seconds;

  linkCodeCountdownTimer = setInterval(() => {
    remaining--;
    if (remaining <= 0) {
      clearInterval(linkCodeCountdownTimer);
      if (timerEl) timerEl.textContent = "Kod muddati tugadi. Yangisini oling.";
      return;
    }
    const mins = Math.floor(remaining / 60);
    const secs = remaining % 60;
    if (timerEl) timerEl.textContent = `Kod amal qilish muddati: ${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }, 1000);
}

// ==========================================
// MODALS & FORMS SUBMISSION
// ==========================================
function setupModalListeners() {
  // Customer Form
  const formCust = document.getElementById('form-new-customer');
  if (formCust) {
    formCust.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        full_name: document.getElementById('cust-name').value.trim(),
        phone_number: document.getElementById('cust-phone').value.trim(),
        credit_limit: document.getElementById('cust-limit').value || "0.00",
        notes: document.getElementById('cust-notes').value.trim()
      };
      try {
        await apiRequest('/customers/', { method: 'POST', body: JSON.stringify(payload) });
        showToast("Yangi mijoz muvaffaqiyatli qo'shildi!", 'success');
        closeModal('modal-new-customer');
        formCust.reset();
        await loadCustomersData();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // Debt Form
  const formDebt = document.getElementById('form-new-debt');
  if (formDebt) {
    formDebt.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        customer_id: document.getElementById('debt-customer-select').value,
        amount: document.getElementById('debt-amount').value,
        description: document.getElementById('debt-desc').value.trim(),
        due_date: document.getElementById('debt-due-date').value || null
      };
      try {
        await apiRequest('/debts/', { method: 'POST', body: JSON.stringify(payload) });
        showToast("Qarz bitimi muvaffaqiyatli rasmiylashtirildi!", 'success');
        closeModal('modal-new-debt');
        formDebt.reset();
        await refreshCurrentView();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // Payment Form
  const formPay = document.getElementById('form-new-payment');
  if (formPay) {
    formPay.addEventListener('submit', async (e) => {
      e.preventDefault();
      const method = document.getElementById('pay-method').value;
      const totalAmount = document.getElementById('pay-amount').value;
      
      const payload = {
        debt_id: document.getElementById('pay-debt-id').value,
        payment_method: method,
        amount: totalAmount,
        notes: document.getElementById('pay-notes').value.trim()
      };

      if (method === 'MIXED') {
        payload.cash_amount = document.getElementById('pay-cash-portion').value || "0.00";
        payload.card_amount = document.getElementById('pay-card-portion').value || "0.00";
      }

      try {
        const res = await apiRequest('/payments/', { method: 'POST', body: JSON.stringify(payload) });
        showToast("To'lov muvaffaqiyatli qabul qilindi!", 'success');
        closeModal('modal-new-payment');
        formPay.reset();
        if (res.data) renderReceiptPreview(res.data);
        await refreshCurrentView();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // Login Form
  const formLogin = document.getElementById('form-login');
  if (formLogin) {
    formLogin.addEventListener('submit', handleLoginSubmit);
  }

  // Register Form
  const formReg = document.getElementById('form-register');
  if (formReg) {
    formReg.addEventListener('submit', handleRegisterSubmit);
  }

  // Forgot Password Form
  const formForgot = document.getElementById('form-forgot');
  if (formForgot) {
    formForgot.addEventListener('submit', handleForgotPasswordSubmit);
  }

  // Change Password Form
  const formChangePassword = document.getElementById('form-change-password');
  if (formChangePassword) {
    formChangePassword.addEventListener('submit', handleChangePasswordSubmit);
  }

  // New Shop Form
  const formShop = document.getElementById('form-new-shop');
  if (formShop) {
    formShop.addEventListener('submit', handleCreateShopSubmit);
  }
}

function updateSettingsUI() {
  const shopNameInput = document.getElementById('settings-shop-name');
  const shopBranchInput = document.getElementById('settings-shop-branch');
  const shopCurrencyInput = document.getElementById('settings-shop-currency');
  const userEmailInput = document.getElementById('settings-user-email');
  const userRoleInput = document.getElementById('settings-user-role');
  const userPhoneInput = document.getElementById('settings-user-phone');

  if (shopNameInput) shopNameInput.value = state.activeShop?.name || 'Do\'kon tanlanmagan';
  if (shopBranchInput) shopBranchInput.value = state.activeShop?.branches?.[0]?.name || 'Asosiy filial #01';
  if (shopCurrencyInput) shopCurrencyInput.value = (state.activeShop?.currency || 'UZS') + ' (Valyuta)';

  if (userEmailInput) userEmailInput.value = state.user?.email || '-';
  if (userRoleInput) {
    const roleName = state.user?.role === 'SUPER_ADMIN' ? 'Bosh Administrator' : (state.user?.role === 'SHOP_OWNER' ? 'Do\'kon Egasi' : (state.user?.role === 'MANAGER' ? 'Menejer' : 'Kassir'));
    userRoleInput.value = roleName;
  }
  if (userPhoneInput) userPhoneInput.value = state.user?.phone_number || '-';
}

async function handleChangePasswordSubmit(e) {
  e.preventDefault();
  const oldPassword = document.getElementById('chg-old-password').value;
  const newPassword = document.getElementById('chg-new-password').value;
  const newConfirm = document.getElementById('chg-new-confirm').value;

  if (newPassword !== newConfirm) {
    showToast("Yangi maxfiy parollar bir xil emas!", 'error');
    return;
  }

  if (newPassword.length < 8) {
    showToast("Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak!", 'error');
    return;
  }

  const submitBtn = e.target.querySelector('button[type="submit"]');
  const origText = submitBtn ? submitBtn.innerHTML : '';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = 'Parol yangilanmoqda...';
  }

  try {
    await apiRequest('/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
        new_password_confirm: newConfirm
      })
    });

    showToast("Parolingiz muvaffaqiyatli almashtirildi!", 'success');
    e.target.reset();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = origText;
    }
  }
}

function openNewDebtModal(customerId = '', customerName = '') {
  if (!state.customers || state.customers.length === 0) {
    showToast("Qarz bitimi rasmiylashtirishdan oldin yangi mijoz qo'shing!", "info");
    openModal('modal-new-customer');
    return;
  }
  const select = document.getElementById('debt-customer-select');
  if (select) {
    select.innerHTML = state.customers.map(c => `
      <option value="${c.id}" ${c.id === customerId ? 'selected' : ''}>${escapeHtml(c.full_name)} (${escapeHtml(c.phone_number)})</option>
    `).join('');
  }
  openModal('modal-new-debt');
}

function openPaymentModal(debtId, customerName, remainingBalance) {
  document.getElementById('pay-debt-id').value = debtId;
  document.getElementById('pay-customer-name-display').textContent = customerName;
  document.getElementById('pay-remaining-balance-display').textContent = formatMoney(remainingBalance) + ' UZS';
  document.getElementById('pay-amount').value = remainingBalance;
  document.getElementById('pay-amount').max = remainingBalance;
  openModal('modal-new-payment');
}

async function promptCancelDebt(debtId) {
  const reason = prompt("Qarzni bekor qilish sababini kiriting:");
  if (!reason) return;
  try {
    await apiRequest(`/debts/${debtId}/cancel/`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    });
    showToast("Qarz muvaffaqiyatli bekor qilindi!", 'success');
    await loadDebtsData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function promptReversePayment(paymentId) {
  const reason = prompt("To'lovni bekor qilish sababini kiriting:");
  if (!reason) return;
  try {
    await apiRequest(`/payments/${paymentId}/reverse/`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    });
    showToast("To'lov muvaffaqiyatli bekor qilindi va qarz balansi tiklandi!", 'success');
    await loadPaymentsData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) {
    m.classList.remove('hidden');
    m.classList.add('flex');
  }
}

function closeModal(modalId) {
  // If user is unauthenticated, NEVER allow closing the authentication modal
  if (modalId === 'modal-auth' && !state.token) {
    return;
  }
  const m = document.getElementById(modalId);
  if (m) {
    m.classList.add('hidden');
    m.classList.remove('flex');
  }
}

// ==========================================
// UTILITY FUNCTIONS
// ==========================================
function formatMoney(amount) {
  if (amount === null || amount === undefined) return "0";
  const num = parseFloat(amount);
  if (isNaN(num)) return "0";
  return num.toLocaleString('uz-UZ', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function formatDateTime(dtStr) {
  if (!dtStr) return '-';
  const d = new Date(dtStr);
  return d.toLocaleDateString('uz-UZ', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function isPastDue(dueDateStr, status) {
  if (!dueDateStr || status === 'PAID' || status === 'CANCELLED') return false;
  return new Date(dueDateStr) < new Date();
}

function getStatusBadge(status) {
  switch (status) {
    case 'UNPAID':
      return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">To'lanmagan</span>`;
    case 'PARTIALLY_PAID':
      return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">Qisman to'langan</span>`;
    case 'OVERDUE':
      return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200 flex items-center justify-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-red-600"></span> Muddati o'tgan</span>`;
    case 'PAID':
      return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">To'langan</span>`;
    case 'CANCELLED':
      return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-500">Bekor qilingan</span>`;
    default:
      return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">${status}</span>`;
  }
}

function getPaymentMethodBadge(method) {
  switch (method) {
    case 'CASH': return 'bg-emerald-50 text-emerald-700 border border-emerald-200';
    case 'CARD': return 'bg-blue-50 text-blue-700 border border-blue-200';
    case 'MIXED': return 'bg-purple-50 text-purple-700 border border-purple-200';
    default: return 'bg-slate-100 text-slate-600';
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  const icon = type === 'success' ? 'check_circle' : (type === 'error' ? 'error' : 'info');
  t.innerHTML = `
    <span class="material-symbols-outlined ${type === 'success' ? 'text-emerald-500' : (type === 'error' ? 'text-red-500' : 'text-blue-500')}">${icon}</span>
    <span>${escapeHtml(message)}</span>
  `;
  container.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transform = 'translateY(12px) scale(0.95)';
    t.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    setTimeout(() => t.remove(), 300);
  }, 4000);
}

// Global bootstrap on window load
if (document.readyState === 'loading') {
  window.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
