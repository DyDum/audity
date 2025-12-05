function getCurrentPath() {
    return window.location.pathname;
}

async function buildSidebar() {
    const container = document.getElementById('sidebar-container');
    if (!container) return;

    // Récupère l'utilisateur pour afficher son nom + filtrer les liens admin
    const me = await apiCall('/api/users/me', 'GET');
    if (!me) {
        return;
    }

    const isAdmin = !!me.is_admin;
    const username = me.username;

    const currentPath = getCurrentPath();

    let html = `
    <div class="position-sticky pt-3">
        <div class="text-center text-white mb-4">
            <h4><i class="fas fa-shield-alt"></i> CIS Manager</h4>
            <small id="username">${username}</small>
        </div>
        <ul class="nav flex-column">
            <li class="nav-item">
                <a class="nav-link ${currentPath === '/dashboard' ? 'active text-white' : ''}" href="/dashboard" id="nav-dashboard">
                <i class="fas fa-home"></i> Tableau de bord
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link ${currentPath === '/servers' ? 'active text-white' : ''}" href="/servers" id="nav-servers">
                <i class="fas fa-server"></i> Serveurs
                </a>
            </li>
    `;

    if (isAdmin) {
        html += `
            <li class="nav-item">
                <a class="nav-link ${currentPath === '/scans' ? 'active text-white' : ''}" href="/scans" id="nav-scans">
                <i class="fas fa-search"></i> Scans
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link ${currentPath === '/scripts' ? 'active text-white' : ''}" href="/scripts" id="nav-scripts">
                <i class="fas fa-file-code"></i> Scripts
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link ${currentPath === '/users' ? 'active text-white' : ''}" href="/users" id="nav-users">
                <i class="fas fa-users"></i> Utilisateurs
                </a>
            </li>
        `;
    }

    html += `
            <li class="nav-item">
                <a class="nav-link ${currentPath === '/account' ? 'active text-white' : ''}" href="/account" id="nav-account">
                <i class="fas fa-user"></i> Mon compte
                </a>
            </li>
            ${isAdmin ? `
            <li class="nav-item">
                <a class="nav-link ${currentPath === '/settings' ? 'active text-white' : ''}" href="/settings" id="nav-settings">
                <i class="fas fa-cog"></i> Paramètres
                </a>
            </li>` : ''}
            </ul>
            <hr class="text-white">
            <ul class="nav flex-column">
            <li class="nav-item">
                <a class="nav-link" href="#" onclick="logout()">
                <i class="fas fa-sign-out-alt"></i> Déconnexion
                </a>
            </li>
        </ul>
    </div>
    `;

    container.innerHTML = html;
    await checkAuth();
}

document.addEventListener('DOMContentLoaded', buildSidebar);
