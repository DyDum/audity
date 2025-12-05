function showAlert(message, type = 'danger') {
    const container = document.getElementById('alert-container');
    if (!container) return;
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alertDiv);

    setTimeout(() => alertDiv.remove(), 5000);
}

async function parseJsonSafe(response) {
    const text = await response.text();
    if (!text) return null;
    try { return JSON.parse(text); } catch { return null; }
}

// Login form
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    // apiCall est JSON, mais /api/auth/login attend form-data OAuth2.
    // On fait un fetch direct, puis on utilisera apiCall pour la suite (MFA + reste de l'app).
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            body: formData
        });
        const text = await response.text();
        const data = text ? JSON.parse(text) : {};

        if (response.ok) {
            if (data.requires_mfa) {
                localStorage.setItem('temp_token', data.access_token);
                document.getElementById('login-form').style.display = 'none';
                document.getElementById('mfa-section').style.display = 'block';
                showAlert('Code MFA requis', 'info');
            } else {
                localStorage.setItem('access_token', data.access_token);
                window.location.href = '/dashboard';
            }
        } else {
            showAlert(data.detail || 'Erreur de connexion', 'danger');
        }
    } catch (error) {
        console.error(error);
        showAlert('Erreur de connexion au serveur', 'danger');
    }
});

// MFA form
document.getElementById('mfa-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const token = localStorage.getItem('temp_token');
    if (!token) {
        showAlert('Session MFA expirée, veuillez vous reconnecter.', 'warning');
        window.location.reload();
        return;
    }

    const mfaCode = document.getElementById('mfa-token').value.trim();
    if (!mfaCode) {
        showAlert('Veuillez entrer le code MFA.', 'warning');
        return;
    }

    // on met le temp_token comme Bearer dans apiCall
    const originalGetToken = window.getToken;
    window.getToken = () => token;  // override temporaire

    const resp = await apiCall('/api/auth/mfa/verify', 'POST', { token: mfaCode });

    // restaurer getToken
    window.getToken = originalGetToken;

    if (!resp) {
        // apiCall a déjà affiché l'erreur (warning/danger)
        return;
    }

    localStorage.removeItem('temp_token');
    localStorage.setItem('access_token', resp.access_token);
    window.location.href = '/dashboard';
});

// Redirection si déjà connecté
if (localStorage.getItem('access_token')) {
    window.location.href = '/dashboard';
}
