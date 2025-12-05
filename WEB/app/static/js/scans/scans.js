setActiveNav('nav-scans');
    
function openNewScanModal() {
    new bootstrap.Modal(document.getElementById('scanModal')).show();
}

async function loadScans() {
    const scans = await apiCall('/api/scans/?limit=20');
    const tbody = document.querySelector('#scans-table tbody');
    
    if (!scans || scans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Aucun scan</td></tr>';
        return;
    }
    
    tbody.innerHTML = scans.map(s => `
        <tr>
            <td>Serveur #${s.server_id}</td>
            <td>${new Date(s.started_at).toLocaleString('fr-FR')}</td>
            <td>Niveau ${s.benchmark_level}</td>
            <td>
                <span class="badge ${s.score >= 80 ? 'bg-success' : s.score >= 60 ? 'bg-warning' : 'bg-danger'}">
                    ${s.score ? s.score.toFixed(1) + '%' : '-'}
                </span>
            </td>
            <td>
                <span class="badge ${s.status === 'completed' ? 'bg-success' : s.status === 'running' ? 'bg-info' : 'bg-secondary'}">
                    ${s.status}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary">Détails</button>
            </td>
        </tr>
    `).join('');
}

async function loadServersForSelect() {
    const servers = await apiCall('/api/servers/');
    const select = document.getElementById('server-select');
    
    if (servers) {
        select.innerHTML = servers.map(s => 
            `<option value="${s.id}">${s.hostname} (${s.ip_address})</option>`
        ).join('');
    }
}

document.getElementById('scan-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const select = document.getElementById('server-select');
    const serverIds = Array.from(select.selectedOptions).map(o => parseInt(o.value));
    
    const data = {
        server_ids: serverIds,
        benchmark_level: parseInt(document.getElementById('benchmark-level').value)
    };
    
    const result = await apiCall('/api/scans/', 'POST', data);
    if (result) {
        showAlert('Scan lancé!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('scanModal')).hide();
        loadScans();
    }
});

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
    loadScans();
    loadServersForSelect();
    setInterval(loadScans, 30000);
});
