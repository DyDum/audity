// Logout
function logout() {
    if (confirm('Êtes-vous sûr ?')) {
        removeToken();
        window.location.href = '/login';
    }
}

// Check authentication
async function checkAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    
    const user = await apiCall('/api/auth/me');
    if (user) {
        if (document.getElementById('username')){
        document.getElementById('username').textContent = user.username;
        }
        
        // Hide admin items if not admin
        if (!user.is_admin) {
            const usersLink = document.getElementById('nav-users');
            const settingsLink = document.getElementById('nav-settings');
            const scansLink = document.getElementById('nav-scans');
            const scriptLink = document.getElementById('nav-scripts');
            if (usersLink) usersLink.parentElement.style.display = 'none';
            if (settingsLink) settingsLink.parentElement.style.display = 'none';
            if (scansLink) scansLink.parentElement.style.display = 'none';
            if (scriptLink) scriptLink.parentElement.style.display = 'none';
        }
        
        return true;
    }
    return false;
}

async function loadCurrentUser() {
    const me = await apiCall('/api/users/me', 'GET');
    if (me) {
        isCurrentUserAdmin = !!me.is_admin;
    } else {
        isCurrentUserAdmin = false;
    }
}