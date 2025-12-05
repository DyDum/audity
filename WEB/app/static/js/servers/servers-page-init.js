setActiveNav('nav-servers');

let servers = [];
let groups = [];
let isCurrentUserAdmin = false;
let osChoiceCurrentServer = null;

async function loadCurrentUser() {
    const me = await apiCall('/api/users/me', 'GET');
    if (me) {
        isCurrentUserAdmin = !!me.is_admin;
    } else {
        isCurrentUserAdmin = false;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadCurrentUser();

    if (!isCurrentUserAdmin) {
        const actions = document.getElementById('server-page-actions');
        if (actions) actions.classList.add('d-none');
        const saveBtn = document.getElementById('edit-server-save-btn');
        if (saveBtn) saveBtn.disabled = true;
    }

    await loadServers();
    await loadGroups();
});
