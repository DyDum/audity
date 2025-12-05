function setActiveNav(navId) {
    document.querySelectorAll('.sidebar a').forEach(a => {
        a.classList.remove('active');
    });
    const activeLink = document.getElementById(navId);
    if (activeLink) {
        activeLink.classList.add('active');
    }
}