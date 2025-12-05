async function apiCall(url, method = 'GET', data = null) {
    const headers = {
        'Content-Type': 'application/json'
    };

    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
        method,
        headers
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);

        // Gestion 401: déconnexion + redirection
        if (response.status === 401) {
            removeToken();
            window.location.href = '/login';
            return null;
        }

        let payload = null;
        const text = await response.text(); // on lit brut
        if (text) {
            try {
                payload = JSON.parse(text);
            } catch {
                payload = text;
            }
        }

        if (!response.ok) {
            // Erreur API: on essaie d'en extraire un message
            let msg = 'Erreur API';
            if (payload) {
                if (typeof payload === 'string') {
                    msg = payload;
                } else if (payload.detail) {
                    if (typeof payload.detail === 'string') {
                        msg = payload.detail;
                    } else if (Array.isArray(payload.detail) && payload.detail.length > 0) {
                        msg = payload.detail[0].msg || JSON.stringify(payload.detail[0]);
                    } else {
                        msg = JSON.stringify(payload.detail);
                    }
                }
            }
            console.warn('API error:', response.status, msg, payload);
            showAlert(msg, 'warning');
            return null;
        }

        return typeof payload === 'string' && !payload ? null : payload;

    } catch (error) {
        console.error('API Error:', error);
        showAlert('Erreur de connexion à l\'API', 'danger');
        return null;
    }
}