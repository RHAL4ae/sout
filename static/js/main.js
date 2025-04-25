/**
 * أرشيف الموسيقى العسكرية الذكي
 * الوظائف والتأثيرات الرئيسية للواجهة
 */

// تنفيذ الكود عندما يتم تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // إضافة التاريخ الحالي في التذييل
    updateFooterYear();
    
    // تفعيل التلميحات (tooltips)
    initTooltips();
    
    // تحسين عرض الصور والرسوم البيانية
    enhanceVisuals();
    
    // إضافة معالجة خاصة لعناصر الصوت
    setupAudioPlayers();
});

/**
 * تحديث سنة حقوق النشر في التذييل
 */
function updateFooterYear() {
    const yearElements = document.querySelectorAll('.current-year');
    const currentYear = new Date().getFullYear();
    
    yearElements.forEach(el => {
        el.textContent = currentYear;
    });
}

/**
 * تفعيل وظيفة التلميحات (tooltips) في البوتستراب
 */
function initTooltips() {
    // تفعيل جميع التلميحات في الصفحة
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * تحسين عرض الصور والرسوم البيانية مع تأثيرات بصرية
 */
function enhanceVisuals() {
    // إضافة تأثير تكبير للصور عند التحويم
    const images = document.querySelectorAll('.card-img-top, .analysis-image');
    
    images.forEach(img => {
        img.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.03)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        img.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // تسلسل ظهور البطاقات عند التمرير
    animateCardsOnScroll();
}

/**
 * إضافة تأثير ظهور تدريجي للبطاقات عند التمرير
 */
function animateCardsOnScroll() {
    const cards = document.querySelectorAll('.card');
    
    // دالة لفحص ما إذا كان العنصر مرئياً في المنفذ
    function isElementInViewport(el) {
        const rect = el.getBoundingClientRect();
        
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
    
    // دالة لإضافة الفئة عند التمرير
    function onScroll() {
        cards.forEach(card => {
            if (isElementInViewport(card)) {
                card.classList.add('animated');
            }
        });
    }
    
    // إضافة مستمع للتمرير
    window.addEventListener('scroll', onScroll);
    
    // تشغيل أول مرة لتحريك العناصر المرئية مبدئياً
    onScroll();
}

/**
 * إعداد عناصر تشغيل الصوت بوظائف إضافية
 */
function setupAudioPlayers() {
    const audioPlayers = document.querySelectorAll('audio');
    
    audioPlayers.forEach(player => {
        // إضافة مستمعي الأحداث
        player.addEventListener('play', function() {
            // إيقاف جميع المشغلات الأخرى عند تشغيل واحد
            audioPlayers.forEach(p => {
                if (p !== player && !p.paused) {
                    p.pause();
                }
            });
            
            // تحديث الواجهة لتعكس حالة التشغيل
            this.closest('.card').classList.add('border-primary');
        });
        
        player.addEventListener('pause', function() {
            this.closest('.card').classList.remove('border-primary');
        });
        
        player.addEventListener('ended', function() {
            this.closest('.card').classList.remove('border-primary');
        });
    });
}

/**
 * وظيفة مساعدة لإظهار رسالة نجاح مؤقتة
 * @param {string} message رسالة النجاح للعرض
 * @param {number} duration مدة العرض بالمللي ثانية
 */
function showSuccessMessage(message, duration = 3000) {
    // إنشاء عنصر التنبيه
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    alert.style.zIndex = '9999';
    alert.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // إضافة العنصر إلى الصفحة
    document.body.appendChild(alert);
    
    // حذف التنبيه بعد المدة المحددة
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(alert);
        }, 300);
    }, duration);
}

/**
 * تحديث عداد المشاهدات لملف محدد (للاستخدام المستقبلي)
 * @param {number} fileId معرف الملف
 */
function updateViewCount(fileId) {
    // هنا ستكون الشيفرة لإرسال طلب AJAX لتحديث العداد
    console.log(`تم عرض الملف برقم المعرف: ${fileId}`);
}
