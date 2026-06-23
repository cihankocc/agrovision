import { useState, useEffect, useRef } from 'react';
import styles from './ResultCard.module.css';

// ── Helpers ────────────────────────────────────────────────────────────────────
function getBadge(conf) {
  if (conf >= 80) return { label: 'Yüksek Güven', cls: styles.badgeHigh };
  if (conf >= 55) return { label: 'Orta Güven',   cls: styles.badgeMid  };
  return               { label: 'Düşük Güven',  cls: styles.badgeLow  };
}
function getBarColor(conf) {
  if (conf >= 80) return styles.barGreen;
  if (conf >= 55) return styles.barAmber;
  return               styles.barRed;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function ResultCard({ icon, iconBg, title, footerNote, result, animDelay = 0 }) {
  const [barWidth, setBarWidth] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const conf = parseFloat(result.confidence);
  const badge = getBadge(conf);

  // Animate bar on mount
  useEffect(() => {
    const t = setTimeout(() => setBarWidth(conf), animDelay + 80);
    return () => clearTimeout(t);
  }, [conf, animDelay]);

  // Sort probs descending
  const sortedProbs = Object.entries(result.all_probs).sort((a, b) => b[1] - a[1]);

  // Sağlıklı durumunda başlık ve ikonu değiştir (backend'den gelen ham label ile kontrol et)
  const isHealthy = title === 'Hastalık Tespiti' && result.label === 'Healthy';
  const displayTitle  = isHealthy ? 'Bitki Sağlığı' : title;
  const displayIcon   = isHealthy ? '✅' : icon;
  const displayIconBg = isHealthy ? '#dcfce7' : iconBg;

  // Gösterilecek etiket: Türkçe varsa onu kullan
  const displayLabel = result.label_tr || result.label;

  return (
    <div className={styles.card} style={{ animationDelay: `${animDelay}ms` }}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.icon} style={{ background: displayIconBg }}>{displayIcon}</div>
        <span className={styles.title}>{displayTitle}</span>
        <span className={`${styles.badge} ${badge.cls}`}>{badge.label}</span>
      </div>

      {/* Body */}
      <div className={styles.body}>
        {/* Main prediction */}
        <div className={styles.predLabel}>{displayLabel}</div>
        <div className={styles.predConf}>{conf.toFixed(1)}% güven</div>

        {/* Confidence bar */}
        <div className={styles.confRow}>
          <span>Güven</span>
          <span>%{conf.toFixed(1)}</span>
        </div>
        <div className={styles.barTrack}>
          <div
            className={`${styles.barFill} ${getBarColor(conf)}`}
            style={{ width: `${Math.min(barWidth, 100)}%` }}
          />
        </div>

        {/* Expand toggle */}
        <button
          className={styles.expandBtn}
          type="button"
          onClick={() => setExpanded(v => !v)}
        >
          <span>{footerNote}</span>
          <span className={`${styles.chevron} ${expanded ? styles.chevronOpen : ''}`}>▾</span>
        </button>

        {/* Probability list */}
        {expanded && (
          <div className={styles.probList}>
            {sortedProbs.map(([cls, pct]) => (
              <div key={cls} className={styles.probRow}>
                <span className={styles.probName} title={cls}>{cls}</span>
                <div className={styles.miniTrack}>
                  <div className={styles.miniFill} style={{ width: `${Math.min(pct, 100)}%` }} />
                </div>
                <span className={styles.probPct}>%{parseFloat(pct).toFixed(1)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Treatment Box (only when diseased) */}
        {result.treatment && result.label !== 'Healthy' && (
          <div className={styles.treatmentBox}>
            <span className={styles.treatmentTitle}>💊 Önerilen Tedavi:</span>
            {result.treatment}
          </div>
        )}
      </div>
    </div>
  );
}
