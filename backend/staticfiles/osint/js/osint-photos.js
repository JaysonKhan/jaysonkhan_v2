/**
 * OSINT Photos — lazy loading queue with IntersectionObserver
 *
 * Rasmlar faqat viewport yaqinida (200px) ko'rinsa yuklanadi.
 * Ko'ringandan keyin ham bir vaqtda max 3 ta parallel so'rov.
 * Agar IntersectionObserver mavjud bo'lmasa (eski browser) — barcha rasmlar
 * to'g'ridan-to'g'ri queue ga tushadi.
 */

var _photoQueue = [];
var _photoLoading = 0;
var _photoMax = 3; // bir vaqtda max 3 ta rasm (Nginx endi 10r/s, burst 30)
var _photoObserver = null;

function initLazyPhotos(container) {
    var imgs = container.querySelectorAll('img[data-lazy-src]');
    if (!imgs.length) return;

    if ('IntersectionObserver' in window) {
        if (!_photoObserver) {
            _photoObserver = new IntersectionObserver(function(entries) {
                for (var i = 0; i < entries.length; i++) {
                    if (entries[i].isIntersecting) {
                        _photoObserver.unobserve(entries[i].target);
                        _photoQueue.push(entries[i].target);
                        _processQueue();
                    }
                }
            }, { rootMargin: '200px' }); // 200px oldindan yuklash
        }
        for (var i = 0; i < imgs.length; i++) _photoObserver.observe(imgs[i]);
    } else {
        // Fallback: eski browserlar uchun barcha rasmlar ketma-ket
        for (var i = 0; i < imgs.length; i++) _photoQueue.push(imgs[i]);
        _processQueue();
    }
}

function _processQueue() {
    while (_photoLoading < _photoMax && _photoQueue.length > 0) {
        _loadPhoto(_photoQueue.shift());
    }
}

function _loadPhoto(img) {
    var src = img.getAttribute('data-lazy-src');
    if (!src) { _processQueue(); return; }
    _photoLoading++;
    img.onload = function() {
        img.removeAttribute('data-lazy-src');
        img.style.display = ''; // ko'rsatish
        _photoLoading--;
        _processQueue();
    };
    img.onerror = function() {
        img.style.display = 'none';
        var fb = img.nextElementSibling;
        if (fb) fb.style.display = 'flex';
        img.removeAttribute('data-lazy-src');
        _photoLoading--;
        _processQueue();
    };
    img.src = src;
}
