import { useRef, useState } from 'react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import styles from './ReportButton.module.css';

// Türkçe ay isimleri
const MONTHS_TR = [
  'Ocak','Şubat','Mart','Nisan','Mayıs','Haziran',
  'Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'
];
const DAYS_TR = ['Pazar','Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi'];

function formatDate(d) {
  return `${DAYS_TR[d.getDay()]}, ${d.getDate()} ${MONTHS_TR[d.getMonth()]} ${d.getFullYear()}`;
}
function formatTime(d) {
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}

export default function ReportButton({ results, location, filename }) {
  const reportRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const now = new Date();

  const disease = results?.disease;
  const weed    = results?.weed;
  const harvest = results?.harvest;

  const handleDownload = async () => {
    setLoading(true);
    try {
      const el = reportRef.current;
      // Önce görünür yap
      el.style.display = 'block';

      const canvas = await html2canvas(el, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#ffffff',
        logging: false,
      });

      el.style.display = 'none';

      const pdf    = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
      const pdfW   = pdf.internal.pageSize.getWidth();
      const pdfH   = pdf.internal.pageSize.getHeight();
      const imgW   = pdfW;
      const imgH   = (canvas.height * imgW) / canvas.width;

      const imgData = canvas.toDataURL('image/png');

      // Birden fazla sayfaya sığdır
      if (imgH <= pdfH) {
        pdf.addImage(imgData, 'PNG', 0, 0, imgW, imgH);
      } else {
        let yPos = 0;
        let remaining = imgH;
        while (remaining > 0) {
          const sliceH = Math.min(pdfH, remaining);
          const srcY   = ((imgH - remaining) / imgH) * canvas.height;
          const sliceCanvas = document.createElement('canvas');
          sliceCanvas.width  = canvas.width;
          sliceCanvas.height = (sliceH / imgH) * canvas.height;
          const ctx = sliceCanvas.getContext('2d');
          ctx.drawImage(canvas, 0, srcY, canvas.width, sliceCanvas.height, 0, 0, canvas.width, sliceCanvas.height);
          if (yPos > 0) pdf.addPage();
          pdf.addImage(sliceCanvas.toDataURL('image/png'), 'PNG', 0, 0, imgW, sliceH);
          remaining -= sliceH;
          yPos += sliceH;
        }
      }

      const safeName = (filename || 'analiz').replace(/\.[^.]+$/, '').replace(/[^a-zA-Z0-9_-]/g, '_');
      pdf.save(`agrovision-rapor-${safeName}-${now.toISOString().slice(0,10)}.pdf`);
    } finally {
      setLoading(false);
    }
  };

  if (!results) return null;

  const confColor = (c) => c >= 80 ? '#166534' : c >= 55 ? '#92400e' : '#991b1b';

  return (
    <>
      <button
        className={styles.btn}
        type="button"
        onClick={handleDownload}
        disabled={loading}
      >
        {loading ? (
          <>⏳ Rapor oluşturuluyor…</>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="12" y1="18" x2="12" y2="12"/>
              <polyline points="9 15 12 18 15 15"/>
            </svg>
            Raporu PDF İndir
          </>
        )}
      </button>

      {/* ─── GİZLİ RAPOR ŞABLONU — html2canvas bunu yakalar ─── */}
      <div ref={reportRef} style={{ display: 'none' }} className={styles.report}>

        {/* Başlık */}
        <div className={styles.rHeader}>
          <div className={styles.rLogo}>🌾</div>
          <div>
            <div className={styles.rTitle}>AgroVision Tarla Analiz Raporu</div>
            <div className={styles.rSubtitle}>Yapay Zeka Destekli Buğday Tarlası Analiz Sistemi</div>
          </div>
        </div>

        {/* Rapor bilgileri */}
        <div className={styles.rMeta}>
          <div className={styles.rMetaRow}>
            <span className={styles.rMetaLabel}>📅 Rapor Tarihi</span>
            <span className={styles.rMetaVal}>{formatDate(now)}</span>
          </div>
          <div className={styles.rMetaRow}>
            <span className={styles.rMetaLabel}>🕐 Saat</span>
            <span className={styles.rMetaVal}>{formatTime(now)}</span>
          </div>
          {filename && (
            <div className={styles.rMetaRow}>
              <span className={styles.rMetaLabel}>🖼️ Analiz Edilen Dosya</span>
              <span className={styles.rMetaVal}>{filename}</span>
            </div>
          )}
          <div className={styles.rMetaRow}>
            <span className={styles.rMetaLabel}>📍 Tarla Konumu</span>
            <span className={styles.rMetaVal}>
              {location
                ? `${location.lat}° Kuzey, ${location.lng}° Doğu`
                : 'Belirtilmedi'}
            </span>
          </div>
        </div>

        {/* Genel Değerlendirme */}
        <div className={styles.rSection}>
          <div className={styles.rSectionTitle}>🔍 Genel Değerlendirme</div>
          <div className={styles.rSummaryBox}>{results.summary}</div>
        </div>

        <div className={styles.rDivider} />

        {/* Hastalık */}
        <div className={styles.rSection}>
          <div className={styles.rSectionTitle}>🦠 Hastalık Analizi</div>
          <div className={styles.rRow}>
            <span className={styles.rRowLabel}>Tespit Edilen Durum</span>
            <span className={styles.rRowVal}>{disease.label_tr}</span>
          </div>
          <div className={styles.rRow}>
            <span className={styles.rRowLabel}>Güven Oranı</span>
            <span className={styles.rRowVal} style={{ color: confColor(disease.confidence) }}>
              %{parseFloat(disease.confidence).toFixed(1)}
            </span>
          </div>
          {disease.treatment && disease.label !== 'Healthy' && (
            <div className={styles.rTreatmentBox}>
              <div className={styles.rTreatmentTitle}>💊 Önerilen Tedavi</div>
              <div className={styles.rTreatmentText}>{disease.treatment}</div>
            </div>
          )}
        </div>

        <div className={styles.rDivider} />

        {/* Yabani Ot */}
        <div className={styles.rSection}>
          <div className={styles.rSectionTitle}>🌿 Yabani Ot Durumu</div>
          <div className={styles.rRow}>
            <span className={styles.rRowLabel}>Durum</span>
            <span className={styles.rRowVal}>{weed.label_tr}</span>
          </div>
          <div className={styles.rRow}>
            <span className={styles.rRowLabel}>Güven Oranı</span>
            <span className={styles.rRowVal} style={{ color: confColor(weed.confidence) }}>
              %{parseFloat(weed.confidence).toFixed(1)}
            </span>
          </div>
        </div>

        <div className={styles.rDivider} />

        {/* Hasat */}
        <div className={styles.rSection}>
          <div className={styles.rSectionTitle}>🌾 Hasat Durumu</div>
          <div className={styles.rRow}>
            <span className={styles.rRowLabel}>Olgunluk Durumu</span>
            <span className={styles.rRowVal}>{harvest.label_tr}</span>
          </div>
          <div className={styles.rRow}>
            <span className={styles.rRowLabel}>Güven Oranı</span>
            <span className={styles.rRowVal} style={{ color: confColor(harvest.confidence) }}>
              %{parseFloat(harvest.confidence).toFixed(1)}
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className={styles.rFooter}>
          Bu rapor AgroVision Yapay Zeka Sistemi tarafından otomatik olarak oluşturulmuştur.
          Kesin tarımsal kararlar için lütfen bir uzmanla görüşünüz.
        </div>
      </div>
    </>
  );
}
