setActiveNav('nav-settings');

document.addEventListener('DOMContentLoaded', async () => {
    const me = await apiCall('/api/users/me', 'GET');
    if (!me) {
        // apiCall gère 401 -> redirection login si tu l'as codé comme ça
        return;
    }
    if (!me.is_admin) {
        window.location.href = '/dashboard';
        return;
    }
});

document.getElementById('azure_enabled').addEventListener('change', function() {
    document.getElementById('azure-config').style.display = this.checked ? 'block' : 'none';
});

document.getElementById('ldap_enabled').addEventListener('change', function() {
    document.getElementById('ldap-config').style.display = this.checked ? 'block' : 'none';
});

async function testAzure() {
    showAlert('Test de connexion Azure...', 'info');
    const result = await apiCall('/api/settings/auth/test-azure', 'POST');
    if (result) {
        showAlert('Connexion Azure réussie!', 'success');
    }
}

async function testLDAP() {
    showAlert('Test de connexion LDAP...', 'info');
    const result = await apiCall('/api/settings/auth/test-ldap', 'POST');
    if (result) {
        showAlert('Connexion LDAP réussie!', 'success');
    }
}

document.getElementById('auth-settings-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        azure_enabled: document.getElementById('azure_enabled').checked,
        azure_client_id: document.getElementById('azure_client_id').value,
        azure_client_secret: document.getElementById('azure_client_secret').value,
        azure_tenant_id: document.getElementById('azure_tenant_id').value,
        ldap_enabled: document.getElementById('ldap_enabled').checked,
        ldap_server: document.getElementById('ldap_server').value,
        ldap_domain: document.getElementById('ldap_domain').value,
        ldap_base_dn: document.getElementById('ldap_base_dn').value,
        mfa_required_for_admins: document.getElementById('mfa_required_for_admins').checked,
        mfa_required_for_users: document.getElementById('mfa_required_for_users').checked
    };
    
    const result = await apiCall('/api/settings/auth', 'PUT', data);
    if (result) {
        showAlert('Paramètres enregistrés!', 'success');
    }
});