const userListEl = document.getElementById('users-list');
const contentListEl = document.getElementById('content-list');
const selectedUserEl = document.getElementById('selected-user');
let selectedUser = null;

async function fetchUsers() {
    try {
        const res = await fetch('/api/users');
        if (res.ok) {
            const users = await res.json();
            userListEl.innerHTML = '';
            users.forEach(u => {
                const btn = document.createElement('button');
                btn.textContent = u.name;
                btn.className = 'user-item' + (selectedUser === u.name ? ' active' : '');
                btn.onclick = () => selectUser(u.name);
                userListEl.appendChild(btn);
            });
        }
    } catch (err) {
        console.error('Error fetching users:', err);
    }
}

async function fetchContent(user) {
    try {
        const res = await fetch(`/api/content/${encodeURIComponent(user)}`);
        if (res.ok) {
            const files = await res.json();
            contentListEl.innerHTML = '';
            files.forEach(f => {
                const li = document.createElement('li');
                li.textContent = f.name;
                contentListEl.appendChild(li);
            });
        }
    } catch (err) {
        console.error('Error fetching content:', err);
    }
}

function selectUser(user) {
    selectedUser = user;
    selectedUserEl.textContent = user;
    fetchContent(user);
}

// Polling interval: cada 5s solo refresca usuarios
setInterval(fetchUsers, 5000);

// Inicial
window.addEventListener('DOMContentLoaded', () => {
    fetchUsers();
});