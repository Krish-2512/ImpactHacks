function loadNotify() {
    fetch('/site/notifications/')  
        .then(response => response.json())
        .then(data => {
            const notificationList = document.getElementById('notification-list');
            notificationList.innerHTML = "";  // Clear previous notifications
            
            data.notifications.forEach(notification => {
                let li = document.createElement('li');
                li.innerHTML = `${notification.message} 
                    <button onclick="deleteNotify(${notification.id})">Delete</button>`;
                notificationList.appendChild(li);
            });
        })
        .catch(error => console.error("Error fetching notifications:", error));
}

function deleteNotify(notificationId) {
    fetch(`/delete-notification/${notificationId}/`, { 
        method: "POST",
        headers: { 
            "X-CSRFToken": getCSRFToken()  // CSRF token for security
        }
    })
    .then(response => response.json())
    .then(() => loadNotify());  // Refresh notifications
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Ensure script runs when page loads
document.addEventListener("DOMContentLoaded", loadNotify);
