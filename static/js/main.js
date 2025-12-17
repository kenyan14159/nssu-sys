// Nit-Sys JavaScript Utilities

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.forEach(function (popoverTriggerEl) {
        new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Time format utilities
const TimeUtils = {
    // Convert mm:ss.xx format to seconds
    parseTime: function(timeStr) {
        if (!timeStr) return null;
        
        const match = timeStr.match(/^(\d{1,2}):(\d{2})\.(\d{2})$/);
        if (!match) return null;
        
        const minutes = parseInt(match[1], 10);
        const seconds = parseInt(match[2], 10);
        const centiseconds = parseInt(match[3], 10);
        
        return minutes * 60 + seconds + centiseconds / 100;
    },
    
    // Convert seconds to mm:ss.xx format
    formatTime: function(totalSeconds) {
        if (totalSeconds === null || totalSeconds === undefined) return '--:--:--';
        
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = Math.floor(totalSeconds % 60);
        const centiseconds = Math.round((totalSeconds % 1) * 100);
        
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${centiseconds.toString().padStart(2, '0')}`;
    },
    
    // Validate time input
    validateTimeInput: function(input) {
        const value = input.value;
        const isValid = /^\d{1,2}:\d{2}\.\d{2}$/.test(value);
        
        if (isValid || value === '') {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        } else {
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
        }
        
        return isValid;
    }
};

// Entry Cart Management
const EntryCart = {
    items: [],
    
    init: function() {
        // Load from session storage if available
        const saved = sessionStorage.getItem('entryCart');
        if (saved) {
            this.items = JSON.parse(saved);
        }
        this.render();
    },
    
    add: function(athleteId, athleteName, raceId, raceName, declaredTime) {
        // Check if already in cart
        const exists = this.items.find(item => 
            item.athleteId === athleteId && item.raceId === raceId
        );
        
        if (exists) {
            this.showToast('既にエントリー済みです', 'warning');
            return false;
        }
        
        this.items.push({
            athleteId,
            athleteName,
            raceId,
            raceName,
            declaredTime
        });
        
        this.save();
        this.render();
        this.showToast('エントリーを追加しました', 'success');
        return true;
    },
    
    remove: function(index) {
        this.items.splice(index, 1);
        this.save();
        this.render();
    },
    
    clear: function() {
        this.items = [];
        this.save();
        this.render();
    },
    
    save: function() {
        sessionStorage.setItem('entryCart', JSON.stringify(this.items));
    },
    
    render: function() {
        const container = document.getElementById('entry-cart-items');
        const badge = document.getElementById('entry-cart-badge');
        const totalEl = document.getElementById('entry-cart-total');
        
        if (!container) return;
        
        if (this.items.length === 0) {
            container.innerHTML = '<p class="text-muted text-center py-3">エントリーはありません</p>';
            if (badge) badge.textContent = '0';
            if (totalEl) totalEl.textContent = '¥0';
            return;
        }
        
        let html = '<ul class="list-group list-group-flush">';
        let total = 0;
        
        this.items.forEach((item, index) => {
            html += `
                <li class="list-group-item d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${item.athleteName}</strong><br>
                        <small class="text-muted">${item.raceName}</small><br>
                        <small>申告: ${item.declaredTime}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="EntryCart.remove(${index})">
                        <i class="bi bi-trash"></i>
                    </button>
                </li>
            `;
            total += 3000; // Entry fee per race
        });
        
        html += '</ul>';
        container.innerHTML = html;
        
        if (badge) badge.textContent = this.items.length;
        if (totalEl) totalEl.textContent = `¥${total.toLocaleString()}`;
    },
    
    showToast: function(message, type) {
        const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'danger'}`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    },
    
    createToastContainer: function() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(container);
        return container;
    }
};

// Check-in functionality
const CheckIn = {
    updateStatus: function(assignmentId, status, csrfToken) {
        fetch(`/heats/checkin/${assignmentId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ status: status })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.updateUI(assignmentId, status);
                EntryCart.showToast('受付状態を更新しました', 'success');
            } else {
                EntryCart.showToast('エラーが発生しました', 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            EntryCart.showToast('通信エラーが発生しました', 'danger');
        });
    },
    
    updateUI: function(assignmentId, status) {
        const row = document.querySelector(`tr[data-assignment-id="${assignmentId}"]`);
        if (!row) return;
        
        const indicator = row.querySelector('.checkin-status');
        indicator.className = 'checkin-status';
        
        switch(status) {
            case 'checked_in':
                indicator.classList.add('checkin-done');
                indicator.innerHTML = '<i class="bi bi-check"></i>';
                break;
            case 'dns':
                indicator.classList.add('checkin-dns');
                indicator.innerHTML = '<i class="bi bi-x"></i>';
                break;
            default:
                indicator.classList.add('checkin-pending');
                indicator.innerHTML = '<i class="bi bi-circle"></i>';
        }
    }
};

// Form validation helpers
const FormValidation = {
    validateEmail: function(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },
    
    validateJaraNumber: function(number) {
        // JARA registration number format
        const re = /^[A-Z]{2}\d{6}$/;
        return re.test(number);
    }
};

// Payment proof image preview
function previewPaymentProof(input) {
    const preview = document.getElementById('payment-proof-preview');
    if (!preview) return;
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// Countdown timer for entry deadline
function initCountdown(targetDate, elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const target = new Date(targetDate).getTime();
    
    const update = function() {
        const now = new Date().getTime();
        const distance = target - now;
        
        if (distance < 0) {
            element.innerHTML = '締切済み';
            return;
        }
        
        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        
        element.innerHTML = `${days}日 ${hours}時間 ${minutes}分`;
    };
    
    update();
    setInterval(update, 60000); // Update every minute
}

// Loading overlay
const LoadingOverlay = {
    show: function() {
        let overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'spinner-overlay';
            overlay.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border text-primary" style="width: 3rem; height: 3rem;" role="status">
                        <span class="visually-hidden">読み込み中...</span>
                    </div>
                    <p class="mt-2">処理中...</p>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        overlay.style.display = 'flex';
    },
    
    hide: function() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
};

// Confirm dialog helper
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Print specific element
function printElement(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
        <head>
            <title>印刷</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { padding: 20px; }
                @media print { .no-print { display: none; } }
            </style>
        </head>
        <body>
            ${element.innerHTML}
            <script>window.onload = function() { window.print(); window.close(); }</script>
        </body>
        </html>
    `);
    printWindow.document.close();
}
