async function deploySshKey(serverId) {
    const sshUsername = document.getElementById('ssh-username').value.trim();
    const sshPassword = document.getElementById('ssh-password').value;

    console.log("Deploying SSH key to server ID:", serverId);
    // 1. Déploiement de la clé SSH
    const response = await apiCall('/api/servers/deploy-ssh-key', 'POST', {
        server_id: serverId,
        ssh_username: sshUsername,
        ssh_password: sshPassword,
    });
    console.log("Deploy response:", response);

    if (!response || !response.success) {
        showAlert(response?.error || "Erreur lors du déploiement de la clé SSH", "danger");
        return;
    }

    showAlert(response.message || "Clé SSH générée et déposée sur le serveur.", "success");

    // 2. Préparation de l’environnement Audity (dossiers + sudoers)
    const prepare = await apiCall('/api/servers/prepare-audity', 'POST', {
        server_id: serverId,
        ssh_username: sshUsername,
        ssh_password: sshPassword,
    });
    console.log("Prepare response:", prepare);

    if (!prepare || !prepare.success) {
        showAlert(prepare?.error || "Erreur lors de la préparation d'Audity", "warning");
        return;
    }

    showAlert(prepare.message || "Environnement Audity préparé (dossiers + sudoers).", "success");
}
