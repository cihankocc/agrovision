import { useState, useRef } from 'react';
import { API_PREDICT } from './config';
import Header           from './components/Header';
import UploadZone       from './components/UploadZone';
import LoadingState     from './components/LoadingState';
import ResultCard       from './components/ResultCard';
import SummaryPanel     from './components/SummaryPanel';
import FertilizerForm   from './components/FertilizerForm';
import MapPicker        from './components/MapPicker';
import styles           from './App.module.css';

// ── Card definitions ──────────────────────────────────────────────────────────
const CARD_CONFIG = [
  { key: 'disease', icon: '🦠', iconBg: '#fef3c7', title: 'Hastalık Tespiti',  footerNote: 'Tüm hastalık olasılıkları', delay: 0   },
  { key: 'weed',    icon: '🌿', iconBg: '#dcfce7', title: 'Yabani Ot Tespiti', footerNote: 'Sınıf dağılımı',            delay: 150 },
  { key: 'harvest', icon: '🌾', iconBg: '#fff7ed', title: 'Hasat Olgunluğu',   footerNote: 'Olgunluk sınıfları',        delay: 300 },
];

export default function App() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const resultsRef = useRef(null);

  // ── Harita konumu ────────────────────────────────────────────────
  const [location, setLocation] = useState(null);

  // ── Analiz ──────────────────────────────────────────────────────
  const handleAnalyze = async (file, setError) => {
    setLoading(true);
    setResults(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(API_PREDICT, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('server');
      const data = await res.json();
      setResults(data);
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (err) {
      setError(
        err.message === 'server'
          ? 'Sunucu hatası oluştu. API sunucusunun çalıştığından emin olun.'
          : 'Bağlantı hatası. Sunucuya erişilemiyor.'
      );
    } finally {
      setLoading(false);
    }
  };

  // ── Sıfırla ─────────────────────────────────────────────────────
  const handleReset = () => {
    setResults(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <>
      <Header />

      <main className={styles.main}>

        {/* ── Harita ── */}
        <MapPicker onLocationSelect={setLocation} />

        {/* ── Fotoğraf Yükleme / Sonuçlar ── */}
        {!results && (
          loading
            ? <LoadingState />
            : <UploadZone onAnalyze={handleAnalyze} loading={loading} />
        )}

        {results && (
          <div ref={resultsRef}>
            <p className={styles.resultsHeading}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                   stroke="#2d7a2d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              Analiz Sonuçları
            </p>

            <div className={styles.cardsGrid}>
              {CARD_CONFIG.map(({ key, icon, iconBg, title, footerNote, delay }) => (
                <ResultCard
                  key={key}
                  icon={icon}
                  iconBg={iconBg}
                  title={title}
                  footerNote={footerNote}
                  result={results[key]}
                  animDelay={delay}
                />
              ))}
            </div>

            <SummaryPanel results={results} onReset={handleReset} location={location} filename={results?._filename} />
          </div>
        )}

        {/* Divider */}
        <div style={{ margin: '40px 0', borderBottom: '2px dashed #a5c4a5', opacity: 0.5 }} />

        {/* Fertilizer Form */}
        <FertilizerForm />
      </main>

      <footer>
        AgroVision — Buğday Tarlası Analiz Sistemi | Yapay Zeka Destekli
      </footer>
    </>
  );
}
