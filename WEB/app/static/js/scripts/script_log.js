function getExecIdFromUrl() {
        const parts = window.location.pathname.split('/');
        return parts[parts.length - 1]; // /script-log/123
    }

    function renderStatus(status) {
        if (status === 'success') {
            return '<span class="badge bg-success">Succès</span>';
        } else if (status === 'failed') {
            return '<span class="badge bg-danger">Échec</span>';
        } else if (status === 'running') {
            return '<span class="badge bg-info text-dark">En cours</span>';
        } else if (status === 'pending') {
            return '<span class="badge bg-warning text-dark">En attente</span>';
        }
        return status;
    }

    async function loadLog() {
        const execId = getExecIdFromUrl();
        const data = await apiCall(`/api/scripts/executions/${execId}/detail`, 'GET');
        if (!data) {
            document.getElementById('log-output').textContent = 'Erreur de chargement du log.';
            return;
        }

        document.title = `Log script ${data.script_name}`;
        document.getElementById('log-title').textContent =
            `Script ${data.script_name} sur ${data.server_hostname}`;

        document.getElementById('log-server').textContent =
            `${data.server_hostname} (${data.server_ip})`;

        document.getElementById('log-start').textContent =
            data.started_at ? new Date(data.started_at).toLocaleString('fr-FR') : '-';
        document.getElementById('log-end').textContent =
            data.finished_at ? new Date(data.finished_at).toLocaleString('fr-FR') : '-';

        document.getElementById('log-status').innerHTML = renderStatus(data.status);
        document.getElementById('log-user').textContent = data.run_by || '-';

        const stdoutWrapper = document.getElementById('stdout-block');
        const stderrWrapper = document.getElementById('stderr-block');
        const outputWrapper = document.getElementById('output-block');

        const stdoutEl = document.getElementById('log-stdout');
        const stderrEl = document.getElementById('log-stderr');
        const outputEl = document.getElementById('log-output');

        const stdout = (data.stdout || '').trim();
        const stderr = (data.stderr || '').trim();

        // reset layout
        stdoutWrapper.className = 'mb-3';
        stderrWrapper.className = 'mb-3';
        outputWrapper.className = 'mb-3';
        stdoutWrapper.classList.add('d-none');
        stderrWrapper.classList.add('d-none');
        outputWrapper.classList.add('d-none');

        if (stdout && stderr) {
            // deux colonnes
            stdoutWrapper.className = 'col-md-6 mb-3';
            stderrWrapper.className = 'col-md-6 mb-3';

            // on met les wrappers dans une row
            const row = document.getElementById('log-rows');
            row.className = 'row';

            stdoutEl.textContent = stdout;
            stderrEl.textContent = stderr;
            stdoutWrapper.classList.remove('d-none');
            stderrWrapper.classList.remove('d-none');
            document.getElementById('titre_stdout').innerHTML = '<h6>Sortie standard</h6>';
            document.getElementById('titre_stderr').innerHTML = '<h6>Sortie d\'erreur</h6>';
        } else if (stdout) {
            const row = document.getElementById('log-rows');
            row.className = '';  // une seule colonne pleine largeur
            stdoutEl.textContent = stdout;
            stdoutWrapper.className = 'mb-3';
            stdoutWrapper.classList.remove('d-none');
        } else if (stderr) {
            const row = document.getElementById('log-rows');
            row.className = '';
            stderrEl.textContent = stderr;
            stderrWrapper.className = 'mb-3';
            stderrWrapper.classList.remove('d-none');
        } else {
            const row = document.getElementById('log-rows');
            row.className = '';
            outputEl.textContent = data.output || 'Aucun retour';
            outputWrapper.classList.remove('d-none');
        }
    }

    document.addEventListener('DOMContentLoaded', loadLog);