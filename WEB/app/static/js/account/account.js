setActiveNav('nav-account');

async function loadAccountInfo() {
    const me = await apiCall('/api/users/me', 'GET');
    if (!me) return;

    const elUser = document.getElementById('acc-username');
    const elEmail = document.getElementById('acc-email');
    const elEmailInfo = document.getElementById('acc-email-info');
    const mfaStatusSpan = document.getElementById('acc-mfa-status');
    const pill = document.getElementById('mfa-status-pill');

    if (elUser) elUser.textContent = me.username;
    if (elEmailInfo) elEmailInfo.textContent = me.email || '-';
    if (elEmail) elEmail.textContent = me.email || '-';

    if (!mfaStatusSpan || !pill) return;

    if (me.mfa_enabled) {
        mfaStatusSpan.textContent = 'Activé';
        mfaStatusSpan.className = 'badge bg-success';
        pill.textContent = 'MFA activé';
        pill.className = 'badge bg-success';
        document.getElementById('mfa-disabled-block')?.classList.add('d-none');
        document.getElementById('mfa-enabled-block')?.classList.remove('d-none');
    } else {
        mfaStatusSpan.textContent = 'Désactivé';
        mfaStatusSpan.className = 'badge bg-secondary';
        pill.textContent = 'MFA désactivé';
        pill.className = 'badge bg-secondary';
        document.getElementById('mfa-disabled-block')?.classList.remove('d-none');
        document.getElementById('mfa-enabled-block')?.classList.add('d-none');
    }
}

// Activer MFA : étape 1 -> enable + ouverture modale
document.getElementById('btn-mfa-enable').addEventListener('click', async () => {
    const resp = await apiCall('/api/auth/mfa/enable', 'POST');
    if (!resp) return;

    const secretEl = document.getElementById('mfa-secret-text');
    const qrEl = document.getElementById('mfa-qr-img');

    if (secretEl) secretEl.textContent = resp.secret;
    if (qrEl) qrEl.src = resp.qr_code_url;

    const modalEl = document.getElementById('mfaSetupModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
});

// Valider le MFA (code TOTP) pour finaliser l’activation
document.getElementById('mfa-setup-verify-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const code = document.getElementById('mfa-setup-code').value.trim();
    if (!code) {
        showAlert('Veuillez entrer le code MFA.', 'warning');
        return;
    }

    const resp = await apiCall('/api/auth/mfa/verify', 'POST', { token: code });
    if (!resp) return;

    showAlert('MFA activé pour votre compte.', 'success');
    document.getElementById('mfa-setup-code').value = '';

    const modalEl = document.getElementById('mfaSetupModal');
    bootstrap.Modal.getInstance(modalEl).hide();

    await loadAccountInfo();
});

// Désactiver le MFA
document.getElementById('btn-mfa-disable').addEventListener('click', async () => {
    if (!confirm('Voulez-vous vraiment désactiver le MFA ?')) return;

    const resp = await apiCall('/api/auth/mfa/disable', 'POST');
    if (!resp) return;

    showAlert(resp.message || 'MFA désactivé.', 'success');
    await loadAccountInfo();
});

// Changer mot de passe
document.getElementById('change-password-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const oldPw = document.getElementById('old-password').value;
    const newPw = document.getElementById('new-password').value;

    const resp = await apiCall('/api/users/me/change-password', 'POST', {
        old_password: oldPw,
        new_password: newPw,
    });
    if (!resp) return;

    showAlert(resp.message || 'Mot de passe modifié.', 'success');
    e.target.reset();
});

// Changer email
document.getElementById('change-email-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const newEmail = document.getElementById('new-email').value.trim();
    if (!newEmail) {
        showAlert("Veuillez saisir une adresse email.", "warning");
        return;
    }

    const resp = await apiCall('/api/users/me/change-email', 'POST', {
        new_email: newEmail,
    });
    if (!resp) return;

    showAlert(resp.message || 'Adresse email mise à jour.', 'success');
    document.getElementById('new-email').value = '';
    await loadAccountInfo();
});

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadAccountInfo();
});
