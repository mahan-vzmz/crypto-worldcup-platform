document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const htmlElement = document.documentElement;

    // Load saved theme or prefer dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    htmlElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = htmlElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            htmlElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }

    function updateThemeIcon(theme) {
        if (!themeIcon) return;
        if (theme === 'dark') {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        } else {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        }
    }

    // Number Counter Animation
    const counters = document.querySelectorAll('.stat-value');
    const speed = 200;

    const animateCounters = () => {
        counters.forEach(counter => {
            const updateCount = () => {
                const targetText = counter.getAttribute('data-target');
                if (!targetText) return;
                
                const target = +targetText;
                let countText = counter.innerText;
                // remove non-numeric for parsing
                const count = +countText.replace(/\D/g, '');
                
                const inc = target / speed;

                if (count < target) {
                    let newVal = Math.ceil(count + inc);
                    counter.innerText = newVal + (targetText.includes('+') ? '+' : '');
                    setTimeout(updateCount, 20);
                } else {
                    counter.innerText = target + (targetText.includes('+') ? '+' : '');
                    // Convert to Persian numerals
                    counter.innerText = counter.innerText.replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
                }
            };
            updateCount();
        });
    }

    // Run animation when elements are in view
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounters();
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        const statsSection = document.querySelector('.stats-row');
        if (statsSection) {
            observer.observe(statsSection);
        }
    } else {
        animateCounters();
    }

    // Market Filtering, sorting and sparklines
    setupFilters();
    setupSorting();
    renderSparklines();

    // Re-apply everything after an HTMX swap (the table is replaced wholesale)
    document.body.addEventListener('htmx:afterSwap', function(event) {
        if (event.detail.target.id === 'crypto-table-container') {
            applyFilters();
            applyCurrentSort();
            renderSparklines();
        }
    });
});

let currentTab = 'all';

function setupFilters() {
    const tabs = document.querySelectorAll('.market-tab');
    const searchInput = document.getElementById('market-search');

    if (!tabs.length || !searchInput) return;

    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            tabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            currentTab = e.target.getAttribute('data-filter');
            applyFilters();
        });
    });

    searchInput.addEventListener('input', () => {
        applyFilters();
    });
}

function applyFilters() {
    const searchInput = document.getElementById('market-search');
    if (!searchInput) return;
    
    const query = searchInput.value.toLowerCase().trim();
    const rows = document.querySelectorAll('.market-row');
    const tbody = document.getElementById('market-tbody');
    let visibleCount = 0;

    if (!rows || rows.length === 0) return;

    rows.forEach(row => {
        const type = row.getAttribute('data-type');
        const name = row.getAttribute('data-name') || '';
        const symbol = row.getAttribute('data-symbol') || '';

        const matchesTab = (currentTab === 'all' || type === currentTab);
        const matchesSearch = (name.includes(query) || symbol.includes(query));

        if (matchesTab && matchesSearch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    // Handle empty state within table
    let noResultsMsg = document.getElementById('no-results-msg');
    if (visibleCount === 0 && rows.length > 0) {
        if (!noResultsMsg && tbody) {
            noResultsMsg = document.createElement('tr');
            noResultsMsg.id = 'no-results-msg';
            noResultsMsg.innerHTML = `<td colspan="9" class="text-center text-muted" style="padding: 3rem 1rem;">هیچ نتیجه‌ای یافت نشد.</td>`;
            tbody.appendChild(noResultsMsg);
        } else if (noResultsMsg) {
            noResultsMsg.style.display = '';
        }
    } else if (noResultsMsg) {
        noResultsMsg.style.display = 'none';
    }
}

// --- Sortable columns ---
let currentSort = { key: null, dir: 'desc' };

function setupSorting() {
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const key = th.getAttribute('data-sort');
            if (currentSort.key === key) {
                currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.key = key;
                currentSort.dir = th.getAttribute('data-default-dir') || 'desc';
            }
            applyCurrentSort();
        });
    });
}

function applyCurrentSort() {
    if (!currentSort.key) return;
    const tbody = document.getElementById('market-tbody');
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll('.market-row'));
    const key = currentSort.key;
    const factor = currentSort.dir === 'asc' ? 1 : -1;

    rows.sort((a, b) => {
        const av = parseFloat(a.getAttribute('data-' + key)) || 0;
        const bv = parseFloat(b.getAttribute('data-' + key)) || 0;
        return (av - bv) * factor;
    });

    rows.forEach(row => tbody.appendChild(row));

    // Reflect sort state on the headers
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        if (th.getAttribute('data-sort') === key) {
            th.classList.add(currentSort.dir === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    });
}

// --- 7-day sparklines (inline SVG) ---
function renderSparklines() {
    document.querySelectorAll('.sparkline-cell').forEach(cell => {
        const raw = cell.getAttribute('data-spark') || '';
        const pts = raw.split(',').map(s => parseFloat(s)).filter(n => !isNaN(n));

        if (pts.length < 2) {
            cell.innerHTML = '<span class="text-muted">—</span>';
            return;
        }

        const w = 120, h = 36;
        const min = Math.min(...pts), max = Math.max(...pts);
        const range = (max - min) || 1;
        const step = w / (pts.length - 1);

        const d = pts.map((p, i) => {
            const x = (i * step).toFixed(1);
            const y = (h - ((p - min) / range) * h).toFixed(1);
            return `${i === 0 ? 'M' : 'L'}${x},${y}`;
        }).join(' ');

        const up = pts[pts.length - 1] >= pts[0];
        cell.innerHTML =
            `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">` +
            `<path class="${up ? 'spark-up' : 'spark-down'}" d="${d}" fill="none" stroke-width="1.5" ` +
            `stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    });
}
