setActiveNav('nav-scripts');
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
    loadScripts();
});

let scripts = [];
let servers = [];

async function loadScripts() {
    const data = await apiCall('/api/scripts/', 'GET');
    if (!data) return;
    scripts = data;

    const tbody = document.querySelector('#scripts-table tbody');
    tbody.innerHTML = '';
    for (const s of scripts) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${s.name}</strong></td>
            <td>${s.description || '-'}</td>
            <td>${s.os_type}</td>
            <td>${s.is_active ? '<span class="badge bg-success">Oui</span>' : '<span class="badge bg-secondary">Non</span>'}</td>
            <td>
                <button class="btn btn-sm btn-outline-secondary" onclick="openEditScriptModal(${s.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-primary" onclick="openRunScriptModal(${s.id})">
                    <i class="fas fa-play"></i>
                </button>
                <button class="btn btn-sm btn-info" onclick="openScriptHistory(${s.id})">
                    <i class="fas fa-clock"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteScript(${s.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    }
}

function openCreateScriptModal() {
    document.getElementById('script-id').value = '';
    document.getElementById('script-name').value = '';
    document.getElementById('script-description').value = '';
    document.getElementById('script-os').value = 'any';
    document.getElementById('script-content').value = '';
    document.getElementById('scriptModalLabel').textContent = 'Nouveau script';
    new bootstrap.Modal(document.getElementById('scriptModal')).show();
}

function openEditScriptModal(id) {
    const s = scripts.find(x => x.id === id);
    if (!s) return;

    document.getElementById('script-id').value = s.id;
    document.getElementById('script-name').value = s.name;
    document.getElementById('script-description').value = s.description || '';
    document.getElementById('script-os').value = s.os_type || 'any';
    document.getElementById('script-content').value = s.content || '';
    document.getElementById('scriptModalLabel').textContent = 'Modifier le script';
    new bootstrap.Modal(document.getElementById('scriptModal')).show();
}

document.getElementById('script-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('script-id').value;
    const payload = {
        name: document.getElementById('script-name').value,
        description: document.getElementById('script-description').value || null,
        os_type: document.getElementById('script-os').value,
        content: document.getElementById('script-content').value,
    };

    let resp;
    if (id) {
        resp = await apiCall(`/api/scripts/${id}`, 'PUT', payload);
    } else {
        resp = await apiCall('/api/scripts/', 'POST', payload);
    }
    if (!resp) return;
    showAlert('Script enregistré.', 'success');
    bootstrap.Modal.getInstance(document.getElementById('scriptModal')).hide();
    loadScripts();
});

async function deleteScript(id) {
    if (!confirm('Désactiver ce script ?')) return;
    const resp = await apiCall(`/api/scripts/${id}`, 'DELETE');
    if (!resp) return;
    showAlert(resp.message || 'Script désactivé.', 'success');
    loadScripts();
}

// Exécution

async function loadServersForRun() {
    const data = await apiCall('/api/servers/list', 'GET');
    if (!data) return;
    servers = data;

    const container = document.getElementById('run-script-servers-list');
    container.innerHTML = '';
    for (const s of servers) {
        const div = document.createElement('div');
        div.className = 'form-check';
        div.innerHTML = `
            <input class="form-check-input" type="checkbox" value="${s.id}" id="run-server-${s.id}">
            <label class="form-check-label" for="run-server-${s.id}">
                ${s.hostname} (${s.ip_address})
            </label>
        `;
        container.appendChild(div);
    }
}

async function openRunScriptModal(id) {
    document.getElementById('run-script-id').value = id;
    await loadServersForRun();
    new bootstrap.Modal(document.getElementById('runScriptModal')).show();
}

document.getElementById('run-script-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const scriptId = document.getElementById('run-script-id').value;
    const checked = Array.from(document.querySelectorAll('#run-script-servers-list input[type=checkbox]:checked'));
    const serverIds = checked.map(x => parseInt(x.value, 10));
    if (serverIds.length === 0) {
        showAlert('Veuillez sélectionner au moins un serveur.', 'warning');
        return;
    }
    const resp = await apiCall(`/api/scripts/${scriptId}/run`, 'POST', { server_ids: serverIds });
    if (!resp) return;
    showAlert(resp.message || 'Exécution lancée.', 'success');
    bootstrap.Modal.getInstance(document.getElementById('runScriptModal')).hide();
});

async function loadScriptStats(scriptId) {
    const stats = await apiCall(`/api/scripts/${scriptId}/stats`, 'GET');
    if (!stats) return;
    document.getElementById('se-total').textContent = stats.total;
    document.getElementById('se-success').textContent = stats.success;
    document.getElementById('se-failed').textContent = stats.failed;
    document.getElementById('se-running').textContent = stats.running;
    document.getElementById('se-pending').textContent = stats.pending;
}

async function loadScriptExecutions(scriptId) {
    const data = await apiCall(`/api/scripts/${scriptId}/executions`, 'GET');
    if (!data) return;

    const tbody = document.querySelector('#script-exec-table tbody');
    tbody.innerHTML = '';
    for (const e of data) {
        const server = servers.find(s => s.id === e.server_id);
        const name = server ? `${server.hostname} (${server.ip_address})` : `#${e.server_id}`;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${name}</td>
            <td>
                ${
                    e.status === 'success' ? '<span class="badge bg-success">Succès</span>' :
                    e.status === 'failed' ? '<span class="badge bg-danger">Échec</span>' :
                    e.status === 'running' ? '<span class="badge bg-info text-dark">En cours</span>' :
                    e.status === 'pending' ? '<span class="badge bg-warning text-dark">En attente</span>' :
                    e.status
                }
            </td>
            <td>${e.started_at ? new Date(e.started_at).toLocaleString('fr-FR') : '-'}</td>
            <td>${e.finished_at ? new Date(e.finished_at).toLocaleString('fr-FR') : '-'}</td>
            <td>
                <button class="btn btn-sm btn-outline-secondary" onclick="showExecLog(${e.id})">
                    Voir
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    }
    document.getElementById('script-exec-section').classList.remove('d-none');
}

async function showExecLog(execId) {
    const data = await apiCall(`/api/scripts/executions/${execId}`, 'GET');
    if (!data) return;
    // simple alert ou modale dédiée
    alert(data.output || 'Aucun log');
}

async function loadScriptExecutions(scriptId) {
    const data = await apiCall(`/api/scripts/${scriptId}/executions`, 'GET');
    if (!data) return;

    const tbody = document.querySelector('#script-exec-table tbody');
    tbody.innerHTML = '';
    for (const e of data) {
        const server = servers.find(s => s.id === e.server_id);
        const name = server ? `${server.hostname} (${server.ip_address})` : `#${e.server_id}`;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${name}</td>
            <td>
                ${
                    e.status === 'success' ? '<span class="badge bg-success">Succès</span>' :
                    e.status === 'failed' ? '<span class="badge bg-danger">Échec</span>' :
                    e.status === 'running' ? '<span class="badge bg-info text-dark">En cours</span>' :
                    e.status === 'pending' ? '<span class="badge bg-warning text-dark">En attente</span>' :
                    e.status
                }
            </td>
            <td>${e.started_at ? new Date(e.started_at).toLocaleString('fr-FR') : '-'}</td>
            <td>${e.finished_at ? new Date(e.finished_at).toLocaleString('fr-FR') : '-'}</td>
            <td>
                <button class="btn btn-sm btn-outline-secondary" onclick="showExecLog(${e.id})">
                    Voir
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    }
}

function showExecLog(execId) {
    window.open(`/script-log/${execId}`, '_blank');
}

async function openScriptHistory(scriptId) {
    const script = scripts.find(s => s.id === scriptId);
    if (script) {
        document.getElementById('hist-script-name').textContent = script.name;
    }
    // s'assurer que la liste des serveurs est chargée pour les noms
    if (!servers || servers.length === 0) {
        const srvData = await apiCall('/api/servers/list', 'GET');
        if (srvData) servers = srvData;
    }

    await loadScriptStats(scriptId);
    await loadScriptExecutions(scriptId);

    const modalEl = document.getElementById('scriptHistoryModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}