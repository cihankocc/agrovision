import ReportButton from './ReportButton';
import styles from './SummaryPanel.module.css';

const ROWS = [
  { key: 'disease', icon: '🦠', label: 'Hastalık Durumu'  },
  { key: 'weed',    icon: '🌿', label: 'Yabani Ot Durumu' },
  { key: 'harvest', icon: '🌾', label: 'Hasat Durumu'     },
];

export default function SummaryPanel({ results, onReset, location, hideReset = false, filename }) {
  const summary = results?.summary;

  return (
    <div className={styles.card}>
      {/* Heading */}
      <div className={styles.heading}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
             stroke="#2d7a2d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        Genel Değerlendirme
      </div>

      {/* Akıllı özet mesajı */}
      {summary && (
        <div className={styles.summaryBox}>{summary}</div>
      )}

      {/* Konum bilgisi */}
      {location && (
        <div className={styles.locationRow}>
          <span>📍</span>
          <span>Tarla Konumu:</span>
          <strong>{location.lat}°K, {location.lng}°D</strong>
        </div>
      )}

      {/* Summary rows */}
      {ROWS.map(({ key, icon, label }) => {
        const r = results[key];
        const displayLabel = r.label_tr || r.label;
        return (
          <div key={key} className={styles.row}>
            <span className={styles.rowIcon}>{icon}</span>
            <span className={styles.rowLabel}>{label}</span>
            <div>
              <span className={styles.rowValue}>{displayLabel}</span>
              <span className={styles.rowConf}>(%{parseFloat(r.confidence).toFixed(1)})</span>
            </div>
          </div>
        );
      })}

      {/* Alt butonlar */}
      <div className={styles.actions}>
        <ReportButton results={results} location={location} filename={filename} />
        {!hideReset && (
          <button className={styles.btnAgain} type="button" onClick={onReset}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="1 4 1 10 7 10"/>
              <path d="M3.51 15a9 9 0 1 0 .49-3.56"/>
            </svg>
            Yeni Fotoğraf Analiz Et
          </button>
        )}
      </div>
    </div>
  );
}
