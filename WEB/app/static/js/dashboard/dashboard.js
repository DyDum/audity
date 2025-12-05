setActiveNav('nav-dashboard');

async function loadDashboardStats() {
    const stats = await apiCall('/api/scans/dashboard/stats');
    if (stats) {
        document.getElementById('stat-servers').textContent = stats.total_servers;
        document.getElementById('stat-scans').textContent = stats.total_scans;
        document.getElementById('stat-score').textContent = stats.average_score ? 
            stats.average_score.toFixed(1) + '%' : 'N/A';
        document.getElementById('stat-risk').textContent = stats.servers_at_risk;
    }
}

async function loadRecentScans() {
    const scans = await apiCall('/api/scans/?limit=10');
    const tbody = document.getElementById('recent-scans-table');
    
    if (!scans || scans.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Aucun scan</td></tr>';
        return;
    }
    
    tbody.innerHTML = scans.map(scan => `
        <tr>
            <td>Serveur #${scan.server_id}</td>
            <td>${new Date(scan.started_at).toLocaleString('fr-FR')}</td>
            <td>
                <span class="badge ${scan.score >= 80 ? 'bg-success' : scan.score >= 60 ? 'bg-warning' : 'bg-danger'}">
                    ${scan.score ? scan.score.toFixed(1) + '%' : 'N/A'}
                </span>
            </td>
            <td>
                <span class="badge ${
                    scan.status === 'completed' ? 'bg-success' :
                    scan.status === 'running' ? 'bg-primary' :
                    scan.status === 'failed' ? 'bg-danger' : 'bg-secondary'
                }">
                    ${scan.status}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary">Détails</button>
            </td>
        </tr>
    `).join('');
}

loadDashboardStats();
loadRecentScans();

// Auto-refresh toutes les 30 secondes
setInterval(() => {
    loadDashboardStats();
    loadRecentScans();
}, 30000);