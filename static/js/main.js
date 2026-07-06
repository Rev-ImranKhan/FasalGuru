// ─────────────────────────────────────────────
//  FasalGuru — Main JavaScript
// ─────────────────────────────────────────────

// ── Sidebar Toggle (Mobile) ───────────────────
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
    document.getElementById('overlay').classList.toggle('open');
}
function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('overlay').classList.remove('open');
}

// ── Animated Counters ─────────────────────────
function animateCounters() {
    document.querySelectorAll('.counter, .counter-stat').forEach(el => {
        const target = parseInt(el.dataset.target || el.textContent.replace(/\D/g, '')) || 0;
        const duration = 1800;
        const step = Math.ceil(target / (duration / 16));
        let current = 0;
        const timer = setInterval(() => {
            current = Math.min(current + step, target);
            el.textContent = current.toLocaleString('en-IN');
            if (current >= target) clearInterval(timer);
        }, 16);
    });
}

// ── Tips Carousel ─────────────────────────────
let tipIndex = 0;
let tipTimer = null;

function goTip(index) {
    const slides = document.querySelectorAll('.tip-slide');
    const dots = document.querySelectorAll('.tip-dot');
    if (!slides.length) return;
    slides[tipIndex].classList.remove('active');
    dots[tipIndex].classList.remove('active');
    tipIndex = index;
    slides[tipIndex].classList.add('active');
    dots[tipIndex].classList.add('active');
}

function startTipCarousel() {
    const slides = document.querySelectorAll('.tip-slide');
    if (!slides.length) return;
    tipTimer = setInterval(() => {
        goTip((tipIndex + 1) % slides.length);
    }, 4000);
}

// ── Toast Notification ────────────────────────
function showToast(message, type = 'success') {
    const container = document.querySelector('.flash-container') || (() => {
        const c = document.createElement('div');
        c.className = 'flash-container';
        document.body.appendChild(c);
        return c;
    })();

    const icons = {
        success: 'fa-circle-check',
        danger: 'fa-circle-xmark',
        warning: 'fa-triangle-exclamation',
        info: 'fa-circle-info'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fa-solid ${icons[type] || icons.info}"></i>
        ${message}
        <button onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

// ── Auto-dismiss flash toasts ─────────────────
function autoDismissToasts() {
    document.querySelectorAll('.toast').forEach((toast, i) => {
        setTimeout(() => {
            if (toast.parentElement) toast.remove();
        }, 4000 + i * 500);
    });
}

// ── Scroll Animations ─────────────────────────
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.feature-card, .step-card, .testimonial-card, .crop-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(24px)';
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(el);
    });
}

// ── Detect Page: Reset loading steps ─────────
function resetLoadingSteps() {
    ['ls1', 'ls2', 'ls3'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.remove('active');
    });
}

// ── Init on DOM Ready ─────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Counters
    animateCounters();

    // Tips
    startTipCarousel();

    // Auto dismiss toasts
    autoDismissToasts();

    // Scroll animations (public pages only)
    if (!document.querySelector('.sidebar')) {
        initScrollAnimations();
    }

    // Reset loading steps if detect page
    if (document.getElementById('resultLoading')) {
        resetLoadingSteps();
    }

    // Highlight active nav on mobile
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Close modal on Escape
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            const modal = document.getElementById('reportModal');
            if (modal) modal.classList.remove('active');
        }
    });
});
