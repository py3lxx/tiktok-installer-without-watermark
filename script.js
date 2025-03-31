document.addEventListener('DOMContentLoaded', () => {
    const videoUrl = document.getElementById('videoUrl');
    const downloadBtn = document.getElementById('downloadBtn');
    const result = document.getElementById('result');

    downloadBtn.addEventListener('click', async () => {
        if (!videoUrl.value) {
            showError('Lütfen bir TikTok video bağlantısı girin');
            return;
        }

        if (!videoUrl.value.includes('tiktok.com')) {
            showError('Lütfen geçerli bir TikTok video bağlantısı girin');
            return;
        }

        // Butonu yükleniyor durumuna getir
        downloadBtn.disabled = true;
        downloadBtn.innerHTML = '<span class="loading"></span> İndiriliyor...';
        result.innerHTML = ''; // Önceki sonuçları temizle
        result.classList.remove('show');

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: videoUrl.value.trim()
                })
            });

            let data;
            try {
                const text = await response.text();
                console.log('Raw response:', text);
                
                try {
                    data = JSON.parse(text);
                } catch (jsonError) {
                    console.error('JSON parse error:', jsonError);
                    throw new Error('Sunucudan geçersiz yanıt alındı');
                }
            } catch (textError) {
                console.error('Text reading error:', textError);
                throw new Error('Sunucu yanıtı okunamadı');
            }
            
            if (response.ok && data) {
                showSuccess(data.downloadUrl);
            } else {
                showError(data?.error || 'Video indirme başarısız oldu');
            }
        } catch (error) {
            console.error('Error:', error);
            showError('Bir hata oluştu: ' + error.message);
        } finally {
            // Butonu normal duruma getir
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = '<i class="fas fa-download"></i> İndir';
        }
    });

    function showError(message) {
        result.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-circle"></i> ${message}
            </div>
        `;
        result.classList.add('show');
        // Hata mesajını görünür alana kaydır
        result.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function showSuccess(downloadUrl) {
        result.innerHTML = `
            <div class="alert alert-success" role="alert">
                <i class="fas fa-check-circle"></i> Video başarıyla indirildi!
                <a href="${downloadUrl}" class="btn btn-success" download>
                    <i class="fas fa-download"></i> Videoyu İndir
                </a>
            </div>
        `;
        result.classList.add('show');
        // Başarı mesajını görünür alana kaydır
        result.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // URL yapıştırma işlemi için event listener
    videoUrl.addEventListener('paste', (e) => {
        e.preventDefault();
        const text = e.clipboardData.getData('text');
        // URL'i temizle
        videoUrl.value = text.trim();
    });
});
