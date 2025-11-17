// Populate elements with data-platform attributes using window.followersData.
// Works with file:// and http(s).
document.addEventListener('DOMContentLoaded', function () {
    const data = window.followersData || {};
    document.querySelectorAll('[data-platform]').forEach(el => {
        const key = el.getAttribute('data-platform');
        el.textContent = (data && data[key]) ? data[key] : '—';
    });
});