async function loadGroups() {
    const data = await apiCall('/api/groups', 'GET');
    if (!data) return;
    groups = data;

    const sel = document.getElementById('edit-group');
    if (!sel) return;

    sel.innerHTML = '<option value="">-- Aucun --</option>';
    for (const g of groups) {
        const opt = document.createElement('option');
        opt.value = g.id;
        opt.textContent = g.name;
        sel.appendChild(opt);
    }
}

async function openEditServerModal(id) {
    await loadGroups();

    const s = servers.find(x => x.id === id);
    if (!s) {
        console.error('Serveur introuvable pour id', id);
        return;
    }

    document.getElementById('edit-server-id').value = s.id;
    document.getElementById('edit-hostname').value = s.hostname || '';
    document.getElementById('edit-ip').value = s.ip_address || '';
    document.getElementById('edit-ssh-port').value = s.ssh_port ?? '';
    document.getElementById('edit-os-type').value = s.os_type || '';
    document.getElementById('edit-group').value = s.group_id || '';

    const modalEl = document.getElementById('editServerModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
}

document.getElementById('edit-server-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit-server-id').value;
    const payload = {
        hostname: document.getElementById('edit-hostname').value,
        ssh_port: document.getElementById('edit-ssh-port').value
            ? parseInt(document.getElementById('edit-ssh-port').value, 10)
            : null,
        os_type: document.getElementById('edit-os-type').value || null,
        group_id: document.getElementById('edit-group').value
            ? parseInt(document.getElementById('edit-group').value, 10)
            : null,
    };

    const data = await apiCall(`/api/servers/${id}`, 'PUT', payload);
    if (!data) return;

    showAlert('Serveur mis à jour', 'success');
    const modalEl = document.getElementById('editServerModal');
    bootstrap.Modal.getInstance(modalEl).hide();
    loadServers();
});

function openCreateGroup() {
    document.getElementById('create-group-name').value = '';
    new bootstrap.Modal(document.getElementById('createGroupModal')).show();
}

document.getElementById('create-group-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('create-group-name').value.trim();
    if (!name) return;
    const resp = await fetch('/api/groups', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name})
    });
    if (resp.ok) {
        bootstrap.Modal.getInstance(document.getElementById('createGroupModal')).hide();
        await loadGroups();
        showAlert('Groupe créé', 'success');
    } else {
        const data = await resp.json();
        showAlert(data.detail || 'Erreur création groupe', 'danger');
    }
});
