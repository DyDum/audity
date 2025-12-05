function openAddServerModal() {
    document.getElementById('server-form').reset();
    new bootstrap.Modal(document.getElementById('serverModal')).show();
}

async function loadServers() {
    const data = await apiCall('/api/servers/list', 'GET');
    if (!data) return;
    servers = data;

    const tbody = document.querySelector('#servers-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    for (const s of servers) {

    let actionsHtml = `
        <button class="btn btn-sm btn-outline-secondary" onclick="openEditServerModal(${s.id})">
            <i class="fas fa-eye"></i>
        </button>
    `;

    if (isCurrentUserAdmin) {
        // Bouton test connexion adapté à l’OS
        if (s.os_type === 'linux') {
            actionsHtml += `
                <button class="btn btn-sm btn-info" onclick="testConnection(${s.id})">
                    <i class="fas fa-plug"></i>
                </button>
                <button class="btn btn-sm btn-primary" onclick="openDeploySshModal(${s.id}, '${s.hostname}')">
                    <i class="fas fa-key"></i>
                </button>
            `;
        } else if (s.os_type === 'windows') {
            actionsHtml += `
                <button class="btn btn-sm btn-info" onclick="testWinrmConnection(${s.id})">
                    <i class="fas fa-plug"></i>
                </button>
                <button class="btn btn-sm btn-primary" onclick="openWinrmModal(${s.id}, '${s.hostname}')">
                    <i class="fas fa-key"></i>
                </button>
            `;
        } else {
            // OS inconnu : proposer un bouton “Configurer” qui ouvre un choix
            actionsHtml += `
                <button class="btn btn-sm btn-warning" onclick="openOsChoiceModal(${s.id}, '${s.hostname}')">
                    <i class="fas fa-question-circle"></i>
                </button>
            `;
        }

        actionsHtml += `
            <button class="btn btn-sm btn-danger" onclick="deleteServer(${s.id})">
                <i class="fas fa-trash"></i>
            </button>
        `;
    }

    const tr = document.createElement('tr');
    tr.innerHTML = `
        <tr>
            <td><strong>${s.hostname}</strong></td>
            <td>${s.ip_address}</td>
            <td>${s.ssh_port || '-'}</td>
            <td>
                <span class="badge ${
                    s.os_type === 'linux' ? 'bg-success'
                    : s.os_type === 'windows' ? 'bg-primary'
                    : 'bg-secondary'
                }">
                    ${s.os_type === 'linux' ? 'Linux' : s.os_type === 'windows' ? 'Windows' : 'Inconnu'}
                </span>
            </td>
            <td>
                ${
                s.connection_status === 'error'
                    ? `<span class="badge bg-warning">Erreur</span>`
                    : s.connection_status === 'connected'
                        ? `<span class="badge bg-success">Connecté</span>`
                    : s.connection_status === 'custom'
                        ? `<span class="badge bg-info text-dark">Accès distant custom (port ${s.ssh_port})</span>`
                    : `<span class="badge bg-secondary text-dark">Hors ligne</span>`
                }
            </td>
            <td>${s.group_name || '-'}</td>
            <td>${s.last_connection ? new Date(s.last_connection).toLocaleString('fr-FR') : '-'}</td>
            <td>${actionsHtml}</td>
        </tr>
    `;
    tbody.appendChild(tr);
}

}

async function testConnection(serverId) {
    showAlert('Test de connexion...', 'info');
    const result = await apiCall(`/api/servers/${serverId}/test-connection`, 'POST');
    if (result) {
        showAlert('Connexion réussie!', 'success');
        loadServers();
    }
}

async function deleteServer(serverId) {
    if (!confirm('Êtes-vous sûr ?')) return;
    const result = await apiCall(`/api/servers/${serverId}`, 'DELETE');
    if (result) {
        showAlert('Serveur supprimé', 'success');
        loadServers();
    }
}

document.getElementById('server-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        hostname: document.getElementById('hostname').value,
        ip_address: document.getElementById('ip_address').value,
        ssh_port: parseInt(document.getElementById('ssh_port').value),
        ssh_username: document.getElementById('ssh_username').value,
        ssh_password: document.getElementById('ssh_password').value,
        group_name: document.getElementById('group_name').value
    };

    const result = await apiCall('/api/servers/', 'POST', data);
    if (result) {
        showAlert('Serveur créé!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('serverModal')).hide();
        loadServers();
    }
});

// Découverte
function openDiscoveryModal() {
    document.getElementById('discovery-form').reset();
    new bootstrap.Modal(document.getElementById('discoveryModal')).show();
}

document.getElementById('discovery-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const range = document.getElementById('network_range').value.trim();
    if (!range) {
        showAlert("Veuillez entrer une plage IP privée.", "danger");
        return;
    }
    const btn = document.querySelector('#discovery-form button[type=submit]');
    btn.disabled = true;
    btn.innerHTML = "Scan en cours...";

    const resp = await fetch("/api/servers/discover", {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${getToken()}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ network_range: range })
    });
    const data = await resp.json();

    btn.disabled = false;
    btn.innerHTML = "Lancer le scan";
    bootstrap.Modal.getInstance(document.getElementById('discoveryModal')).hide();

    if (resp.ok) {
        showAlert(`${data.found} hôtes détectés (${data.added} ajoutés)`, "success");
        loadServers();
    } else {
        showAlert(data.detail || "Erreur lors de la découverte", "danger");
    }
});

// SSH key
function openDeploySshModal(serverId, hostname) {
    document.getElementById('ssh-server-id').value = serverId;
    document.getElementById('ssh-server-host').value = hostname;
    document.getElementById('ssh-username').value = '';
    document.getElementById('ssh-password').value = '';
    new bootstrap.Modal(document.getElementById('deploySshModal')).show();
}

document.getElementById('deploy-ssh-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const serverId = document.getElementById('ssh-server-id').value;
    deploySshKey(serverId);
});

// Discover smart
async function smartDiscoverNetwork() {
    const network = prompt('Plage à scanner (ex: 192.168.1.0/24) ?');
    if (!network) return;
    showAlert('Scan réseau en cours...', "info");
    const data = await apiCall('/api/servers/discover-smart', 'POST', {
        network_range: network
    });
    if (data) {
        showAlert(`${data.added} serveurs ajoutés, ${data.already} déjà présents.`, "success");
        loadServers();
    } else {
        showAlert(data.detail || "Erreur lors du scan", "danger");
    }
}

function openOsChoiceModal(id, hostname) {
    osChoiceCurrentServer = servers.find(s => s.id === id) || null;

    document.getElementById('os-choice-server-id').value = id;
    document.getElementById('os-choice-text').textContent =
        `Type d'OS pour le serveur ${hostname} (${id}) :`;
    document.getElementById('os-choice-select').value = '';

    const modalEl = document.getElementById('osChoiceModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}

document.getElementById('os-choice-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const serverId = document.getElementById('os-choice-server-id').value;
    const osType = document.getElementById('os-choice-select').value;

    if (!osType) {
        showAlert("Veuillez sélectionner un type d'OS.", 'warning');
        return;
    }

    const s = osChoiceCurrentServer || servers.find(x => x.id === parseInt(serverId, 10));
    if (!s) {
        showAlert("Serveur introuvable.", 'danger');
        return;
    }

    // Mise à jour de l'OS côté backend
    const payload = {
        hostname: s.hostname,
        ssh_port: s.ssh_port,
        os_type: osType,
        group_id: s.group_id,
    };

    const data = await apiCall(`/api/servers/${serverId}`, 'PUT', payload);
    if (!data) return;

    showAlert("Type d'OS mis à jour.", 'success');

    // Fermer la modale
    const modalEl = document.getElementById('osChoiceModal');
    bootstrap.Modal.getInstance(modalEl).hide();

    // Recharger la liste pour mettre à jour les badges + boutons
    await loadServers();

    // Enchaîner sur l'action adaptée
    if (osType === 'linux') {
        openDeploySshModal(serverId, s.hostname);
    } else if (osType === 'windows') {
        openWinrmModal(serverId, s.hostname);
    }
});

function openWinrmModal(serverId, hostname) {
    document.getElementById('winrm-server-id').value = serverId;
    document.getElementById('winrm-server-host').value = hostname;
    document.getElementById('winrm-username').value = '';
    document.getElementById('winrm-password').value = '';

    const modalEl = document.getElementById('winrmModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}

document.getElementById('winrm-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const serverId = document.getElementById('winrm-server-id').value;
    const username = document.getElementById('winrm-username').value.trim();
    const password = document.getElementById('winrm-password').value;

    if (!username || !password) {
        showAlert("Veuillez saisir utilisateur et mot de passe WinRM.", "warning");
        return;
    }

    const resp = await apiCall(`/api/servers/${serverId}/winrm-credentials`, 'POST', {
        username,
        password,
    });
    if (!resp) return;

    showAlert(resp.message || "Identifiants WinRM enregistrés.", "success");
    bootstrap.Modal.getInstance(document.getElementById('winrmModal')).hide();
});

async function testWinrmConnection(serverId) {
    showAlert('Test de connexion WinRM...', 'info');
    const result = await apiCall(`/api/servers/${serverId}/test-winrm`, 'POST');
    if (result) {
        showAlert(result.message || 'Connexion WinRM réussie!', 'success');
        loadServers();
    }
}