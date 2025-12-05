setActiveNav('nav-users');

function openAddUserModal() {
    document.getElementById('user-form').reset();
    new bootstrap.Modal(document.getElementById('userModal')).show();
}

async function loadUsers() {
    const users = await apiCall('/api/users/');
    const tbody = document.querySelector('#users-table tbody');
    
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Aucun utilisateur</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(u => `
        <tr>
            <td><strong>${u.username}</strong></td>
            <td>${u.email}</td>
            <td><span class="badge ${u.is_admin ? 'bg-danger' : 'bg-secondary'}">${u.is_admin ? 'Admin' : 'Utilisateur'}</span></td>
            <td><span class="badge ${u.is_active ? 'bg-success' : 'bg-danger'}">${u.is_active ? 'Actif' : 'Inactif'}</span></td>
            <td>${new Date(u.created_at).toLocaleString('fr-FR')}</td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="toggleUserStatus(${u.id}, ${u.is_active})">
                    <i class="fas fa-${u.is_active ? 'lock' : 'unlock'}"></i> ${u.is_active ? 'Désactiver' : 'Activer'}
                </button>
                <button class="btn btn-sm btn-warning" onclick="adminResetMfa(${u.id})">
                    <i class="fas fa-redo"></i> Réinitialiser MFA
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteUser(${u.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function deleteUser(userId) {
    if (!confirm('Êtes-vous sûr ? Cette action est irréversible.')) return;
    const result = await apiCall(`/api/users/${userId}`, 'DELETE');
    if (result) {
        showAlert('Utilisateur supprimé avec succès', 'success');
        loadUsers();
    } else {
        showAlert('Erreur lors de la suppression', 'danger');
    }
}

// IMPORTANT: Soumettre le formulaire
document.getElementById('user-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Récupérer les valeurs du formulaire
    const username = document.getElementById('username_form').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    let full_name = document.getElementById('full_name').value.trim();
    const is_admin = document.getElementById('is_admin').checked;
    
    // ✅ CORRECTION: Convertir full_name
    full_name = full_name === '' ? null : full_name;
    
    // Validations côté client
    if (username.length < 3) {
        showAlert('Le nom d\'utilisateur doit contenir au moins 3 caractères', 'danger');
        return;
    }
    
    if (password.length < 8) {
        showAlert('Le mot de passe doit contenir au moins 8 caractères', 'danger');
        return;
    }
    
    if (!email.includes('@')) {
        showAlert('Email invalide', 'danger');
        return;
    }
    
    // Préparer les données
    const data = {
        username: username,
        email: email,
        password: password,
        full_name: full_name,  // ✅ null si vide, "string" sinon
        is_admin: is_admin
    };
    
    // Envoyer à l'API
    const result = await apiCall('/api/users/', 'POST', data);
    
    if (result) {
        showAlert('Utilisateur créé avec succès !', 'success');
        bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
        loadUsers();
    } else {
        showAlert('Erreur lors de la création de l\'utilisateur', 'danger');
    }
});

// Charger la liste des utilisateurs au chargement
loadUsers();

async function toggleUserStatus(userId, isActive) {
    const action = isActive ? 'désactiver' : 'activer';
    if (!confirm(`Êtes-vous sûr de vouloir ${action} cet utilisateur ?`)) return;
    
    const token = getToken();
    const response = await fetch(`/api/users/${userId}/toggle-status`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    
    const result = await response.json();
    
    if (response.ok) {
        showAlert(result.message || `Utilisateur ${action}é`, 'success');
        loadUsers();
    } else {
        showAlert(result.detail || `Erreur lors de la ${action}`, 'danger');
    }
}

async function adminResetMfa(userId) {
    if (!confirm("Réinitialiser le MFA pour cet utilisateur ?")) return;
    const resp = await apiCall('/api/users/mfa/reset', 'POST', { user_id: userId });
    if (!resp) return;
    showAlert(resp.message, 'success');
}