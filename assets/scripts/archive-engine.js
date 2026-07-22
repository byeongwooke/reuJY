document.addEventListener("DOMContentLoaded", () => {
  // Page entrance fade-in transition trigger
  document.body.classList.add('loaded');

  const urlParams = new URLSearchParams(window.location.search);
  const category = urlParams.get('category');
  
  // Set Category Title
  const titleEl = document.getElementById('category-title');
  if (titleEl) {
    titleEl.innerText = category || 'Archive';
  }

  // Category media map
  const CATEGORY_MAP = {
    "Regard": "photo",
    "Representation": "photo",
    "Touch": "drawing",
    "Texture": "drawing"
  };

  const mediaType = CATEGORY_MAP[category];
  const gridContainer = document.getElementById('archive-grid-container');

  if (!gridContainer) return;

  if (mediaType === "photo") {
    // [사진 영역] 고유 비율을 중시하는 정밀한 Masonry 밀집 그리드 적용
    gridContainer.className = "photo-masonry-grid";
    renderPhotoData();
  } else if (mediaType === "drawing") {
    // [그림 영역] 캔버스의 질감을 살리기 위해 여백을 더 둔 와이드 그리드 적용
    gridContainer.className = "drawing-canvas-grid";
    renderDrawingData();
  } else {
    // Default fallback to show all photography if category is missing or invalid
    gridContainer.className = "photo-masonry-grid";
    if (titleEl) titleEl.innerText = 'Archive';
    renderPhotoData();
  }

  // Initialize lightbox trigger & controls
  initLightbox();
});

/* ─────────────────────────────────────────
   DATASETS & CAPTIONS
───────────────────────────────────────── */
const PHOTOGRAPHY_IMAGES = Array.from({ length: 29 }, (_, i) => `assets/photography/reujy_photography_${i}.jpg`);

const VISUALIZING_IMAGES = [
  'assets/visualizing/reujy_visualizing_0____.jpg',
  'assets/visualizing/reujy_visualizing_1____.jpg',
  'assets/visualizing/reujy_visualizing_2_Feather__16x22_2018.jpg',
  'assets/visualizing/reujy_visualizing_3_Adventure_천에 아크릴_72x117cm_2024.jpg',
  'assets/visualizing/reujy_visualizing_4___40x55cm_2024 (1).jpg',
  'assets/visualizing/reujy_visualizing_5___40x55cm_2024 (2).jpg',
  'assets/visualizing/reujy_visualizing_6___40x55cm_2025 (1).jpg',
  'assets/visualizing/reujy_visualizing_7___45x60cm_2024.jpg',
  'assets/visualizing/reujy_visualizing_8_Candle light_사진캔버스 위에 아크릴_40x57cm_2024.jpg',
  'assets/visualizing/reujy_visualizing_9_Parfume_종이에 립스틱_40x55cm_2025.jpg',
  'assets/visualizing/reujy_visualizing_10_Untitled_종이에 수채와 색연필__2008.jpg',
  'assets/visualizing/reujy_visualizing_11_a man_종이에 수채_16.6x25.5cm_2024.jpg',
  'assets/visualizing/reujy_visualizing_12_a woman in move_종이에 먹과 파스텔_40x55cm_2025.jpg',
  'assets/visualizing/reujy_visualizing_13____.jpg'
];

function getMuseumCaption(src, category, index) {
  if (category === 'photo') {
    return `Photography #${String(index + 1).padStart(2, '0')}`;
  }
  
  try {
    const parts = src.split('/');
    const filename = decodeURIComponent(parts[parts.length - 1]).replace('.jpg', '');
    
    // Format: reujy_visualizing_{index}_{Title}_{Material}_{Size}_{Year}
    const tokens = filename.split('_');
    if (tokens.length >= 4) {
      const detailTokens = tokens.slice(3); // skip 'reujy', 'visualizing', and index
      const cleanTokens = detailTokens.map(t => t.trim()).filter(t => t !== '');
      if (cleanTokens.length > 0) {
        return cleanTokens.join(', ');
      }
    }
  } catch (e) {
    console.error("Caption parsing error:", e);
  }
  
  return `Visual Art #${String(index + 1).padStart(2, '0')}`;
}

/* ─────────────────────────────────────────
   MASONRY RESIZING FOR PHOTO GRID
───────────────────────────────────────── */
const gridResizeObserver = new ResizeObserver((entries) => {
  entries.forEach(entry => {
    resizeGridItem(entry.target);
  });
});

function resizeGridItem(item) {
  const img = item.querySelector('.archive-item-image');
  if (!img) return;

  const setSpan = () => {
    const grid = document.getElementById('archive-grid-container');
    if (!grid || !grid.classList.contains('photo-masonry-grid')) return;

    const rowHeight = parseInt(window.getComputedStyle(grid).getPropertyValue('grid-auto-rows')) || 15;
    const rowGap = parseInt(window.getComputedStyle(grid).getPropertyValue('grid-row-gap')) || 30;
    const imgHeight = img.getBoundingClientRect().height || img.offsetHeight;
    
    if (imgHeight > 0) {
      const rowSpan = Math.ceil((imgHeight + rowGap) / (rowHeight + rowGap));
      item.style.gridRowEnd = `span ${rowSpan}`;
    }
  };

  if (img.complete) {
    setSpan();
  } else {
    img.onload = setSpan;
  }
}

function resizeAllGridItems() {
  const grid = document.getElementById('archive-grid-container');
  if (!grid || !grid.classList.contains('photo-masonry-grid')) return;
  const items = grid.querySelectorAll('.archive-item');
  items.forEach(resizeGridItem);
}

window.addEventListener('resize', resizeAllGridItems);

/* ─────────────────────────────────────────
   RENDERING IMPLEMENTATION
───────────────────────────────────────── */
function renderPhotoData() {
  const gridContainer = document.getElementById('archive-grid-container');
  gridContainer.replaceChildren();

  PHOTOGRAPHY_IMAGES.forEach((src, index) => {
    const item = document.createElement('div');
    item.className = 'archive-item';
    item.style.animationDelay = `${0.04 + index * 0.04}s`;

    const img = document.createElement('img');
    img.src = src;
    img.className = 'archive-item-image';
    img.alt = `사진 작품 — ${index + 1}`;
    img.loading = 'lazy';

    const caption = document.createElement('div');
    caption.className = 'archive-item-caption';
    caption.innerText = getMuseumCaption(src, 'photo', index);

    item.appendChild(img);
    item.appendChild(caption);

    // Lightbox wire-up
    item.addEventListener('click', () => {
      triggerLightbox(src);
    });

    gridContainer.appendChild(item);
    
    // Track for masonry resizing
    gridResizeObserver.observe(item);
    resizeGridItem(item);
  });

  triggerCascade();
}

function renderDrawingData() {
  const gridContainer = document.getElementById('archive-grid-container');
  gridContainer.replaceChildren();

  VISUALIZING_IMAGES.forEach((src, index) => {
    const item = document.createElement('div');
    item.className = 'archive-item';
    item.style.animationDelay = `${0.05 + index * 0.05}s`;

    const img = document.createElement('img');
    img.src = src;
    img.className = 'archive-item-image';
    img.alt = `시각예술 작품 — ${index + 1}`;
    img.loading = 'lazy';

    const caption = document.createElement('div');
    caption.className = 'archive-item-caption';
    caption.innerText = getMuseumCaption(src, 'drawing', index);

    item.appendChild(img);
    item.appendChild(caption);

    // Lightbox wire-up
    item.addEventListener('click', () => {
      triggerLightbox(src);
    });

    gridContainer.appendChild(item);
  });

  triggerCascade();
}

function triggerCascade() {
  const gridContainer = document.getElementById('archive-grid-container');
  const items = gridContainer.querySelectorAll('.archive-item');
  items.forEach(item => {
    item.classList.remove('animate-arrival');
    void item.offsetWidth; // Force layout recalculation
    item.classList.add('animate-arrival');
  });
}

/* ─────────────────────────────────────────
   LIGHTBOX MANAGEMENT
───────────────────────────────────────── */
function initLightbox() {
  const lightboxOverlay = document.getElementById('lightbox-overlay');
  const lightboxClose = document.getElementById('lightbox-close');

  if (lightboxClose && lightboxOverlay) {
    lightboxClose.addEventListener('click', closeLightbox);
    lightboxOverlay.addEventListener('click', (e) => {
      if (e.target === lightboxOverlay) {
        closeLightbox();
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && lightboxOverlay && lightboxOverlay.classList.contains('open')) {
      closeLightbox();
    }
  });
}

function triggerLightbox(src) {
  const lightboxOverlay = document.getElementById('lightbox-overlay');
  const lightboxImg = document.getElementById('lightbox-img');

  if (lightboxOverlay && lightboxImg) {
    lightboxImg.src = src;
    lightboxOverlay.classList.add('open');
    lightboxOverlay.setAttribute('aria-hidden', 'false');
  }
}

function closeLightbox() {
  const lightboxOverlay = document.getElementById('lightbox-overlay');
  const lightboxImg = document.getElementById('lightbox-img');

  if (lightboxOverlay && lightboxImg) {
    lightboxOverlay.classList.remove('open');
    lightboxOverlay.setAttribute('aria-hidden', 'true');
    setTimeout(() => { lightboxImg.src = ''; }, 350);
  }
}
