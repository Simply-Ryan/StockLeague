// league_admin.js
// Handles admin actions on the league detail page: kick, mute, set admin

async function postJson(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(body),
        credentials: 'same-origin'
    });
    return res.json();
}

function showToast(message, title = '', type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toastId = `toast-${Date.now()}`;
    const bgClass = type === 'success' ? 'bg-success text-white' : type === 'error' ? 'bg-danger text-white' : 'bg-secondary text-white';
    const html = `
      <div id="${toastId}" class="toast ${bgClass}" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000">
        <div class="toast-header ${bgClass}">
          <strong class="me-auto">${title || 'Notice'}</strong>
          <small class="text-muted">now</small>
          <button type="button" class="btn-close btn-close-white ms-2" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
          ${message}
        </div>
      </div>
    `;
    container.insertAdjacentHTML('beforeend', html);
    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
    // Remove after hidden
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

let pendingAction = null;
let pendingTarget = null;

function setButtonLoading(btn, isLoading) {
    if (!btn) return;
    if (isLoading) {
        btn.dataset.origText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>${btn.textContent.trim()}`;
    } else {
        btn.disabled = false;
        if (btn.dataset.origText) btn.innerHTML = btn.dataset.origText;
    }
}

function attachLeagueAdminHandlers() {
    // Kick
    document.querySelectorAll('.btn-kick').forEach(btn => {
        btn.addEventListener('click', (e) => {
            pendingAction = 'kick';
            pendingTarget = btn.dataset.userId;
            document.getElementById('confirmModalMessage').textContent = 'Remove this member from the league?';
            const m = new bootstrap.Modal(document.getElementById('confirmModal'));
            m.show();
        });
    });

    // Mute
    document.querySelectorAll('.btn-mute').forEach(btn => {
        btn.addEventListener('click', (e) => {
            pendingAction = 'mute';
            pendingTarget = btn.dataset.userId;
            document.getElementById('muteDuration').value = '';
            const m = new bootstrap.Modal(document.getElementById('muteModal'));
            m.show();
        });
    });

    // Set admin
    document.querySelectorAll('.btn-set-admin').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const userId = btn.dataset.userId;
            const isAdmin = btn.dataset.isAdmin === '1' || btn.dataset.isAdmin === 'true';
            setButtonLoading(btn, true);
            try {
                const resp = await postJson(`/leagues/${LEAGUE_ID}/admin/set_admin`, { target_user_id: userId, is_admin: isAdmin ? 0 : 1 });
                if (resp && resp.ok) {
                    showToast('Admin status updated', 'Success', 'success');
                    window.location.reload();
                } else {
                    showToast(resp.error || 'Failed to update admin status', 'Error', 'error');
                }
            } catch (err) {
                console.error(err);
                showToast('Server error', 'Error', 'error');
            } finally {
                setButtonLoading(btn, false);
            }
        });
    });

    // Confirm modal action
    const confirmBtn = document.getElementById('confirmModalConfirm');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', async (e) => {
            const modalEl = document.getElementById('confirmModal');
            const bsModal = bootstrap.Modal.getInstance(modalEl);
            confirmBtn.disabled = true;
            try {
                if (pendingAction === 'kick') {
                    const btnEl = document.querySelector(`.btn-kick[data-user-id='${pendingTarget}']`);
                    setButtonLoading(btnEl, true);
                    const resp = await postJson(`/leagues/${LEAGUE_ID}/admin/kick`, { target_user_id: pendingTarget });
                    if (resp && resp.ok) {
                        const row = document.getElementById(`member-row-${pendingTarget}`);
                        if (row) row.remove();
                        showToast('Member removed', 'Success', 'success');
                    } else {
                        showToast(resp.error || 'Failed to remove member', 'Error', 'error');
                    }
                    setButtonLoading(btnEl, false);
                }
            } catch (err) {
                console.error(err);
                showToast('Server error', 'Error', 'error');
            } finally {
                confirmBtn.disabled = false;
                bsModal.hide();
                pendingAction = null;
                pendingTarget = null;
            }
        });
    }

    // Mute modal confirm
    const muteConfirm = document.getElementById('muteModalConfirm');
    if (muteConfirm) {
        muteConfirm.addEventListener('click', async (e) => {
            const duration = document.getElementById('muteDuration').value;
            muteConfirm.disabled = true;
            try {
                const btnEl = document.querySelector(`.btn-mute[data-user-id='${pendingTarget}']`);
                setButtonLoading(btnEl, true);
                const payload = { target_user_id: pendingTarget };
                if (duration) payload.minutes = parseInt(duration, 10);
                const resp = await postJson(`/leagues/${LEAGUE_ID}/admin/mute`, payload);
                if (resp && resp.ok) {
                    showToast('Member muted', 'Success', 'success');
                } else {
                    showToast(resp.error || 'Failed to mute member', 'Error', 'error');
                }
                setButtonLoading(btnEl, false);
            } catch (err) {
                console.error(err);
                showToast('Server error', 'Error', 'error');
            } finally {
                muteConfirm.disabled = false;
                const modalEl = document.getElementById('muteModal');
                const bsModal = bootstrap.Modal.getInstance(modalEl);
                bsModal.hide();
                pendingAction = null;
                pendingTarget = null;
            }
        });
    }
}

// Wait for DOM
document.addEventListener('DOMContentLoaded', () => {
    if (typeof LEAGUE_ID === 'undefined') {
        console.warn('LEAGUE_ID not defined; league admin handlers will not attach.');
        return;
    }
    attachLeagueAdminHandlers();
});
