import { useState, useRef, useCallback } from 'react';
import { MAX_FILE_SIZE } from '../config';
import styles from './UploadZone.module.css';

export default function UploadZone({ onAnalyze, loading }) {
  const [file, setFile]         = useState(null);
  const [preview, setPreview]   = useState(null);
  const [dragover, setDragover] = useState(false);
  const [error, setError]       = useState('');
  const fileInputRef = useRef();

  // ── Validation & selection ──────────────────────────────────
  const handleFile = useCallback((f) => {
    setError('');
    if (!f) return;
    if (!['image/jpeg', 'image/png'].includes(f.type)) {
      setError('Lütfen JPG veya PNG formatında bir fotoğraf seçin.');
      return;
    }
    if (f.size > MAX_FILE_SIZE) {
      setError("Dosya boyutu 10 MB'dan büyük olamaz.");
      return;
    }
    setFile(f);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  }, []);

  const clearFile = () => {
    setFile(null);
    setPreview(null);
    setError('');
    fileInputRef.current.value = '';
  };

  const handleAnalyze = () => {
    if (!file) { setError('Lütfen önce bir fotoğraf seçin.'); return; }
    onAnalyze(file, setError);
  };

  // ── Drag & drop ─────────────────────────────────────────────
  const onDragOver  = (e) => { e.preventDefault(); setDragover(true);  };
  const onDragLeave = ()  => setDragover(false);
  const onDrop      = (e) => { e.preventDefault(); setDragover(false); handleFile(e.dataTransfer.files[0]); };
  const onZoneClick = ()  => { if (!file) fileInputRef.current.click(); };

  // ── Render ──────────────────────────────────────────────────
  return (
    <div className={styles.card}>
      {/* Card heading */}
      <div className={styles.cardTitle}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
             stroke="#2d7a2d" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        Fotoğraf Yükle
      </div>

      {/* Drop zone */}
      <div
        className={`${styles.dropZone} ${dragover ? styles.dragover : ''} ${file ? styles.hasFile : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={onZoneClick}
      >
        {!file ? (
          /* Empty state */
          <>
            <div className={styles.dropIcon}>🌾</div>
            <p className={styles.dropText}>Fotoğrafı buraya sürükleyin veya tıklayın</p>
            <p className={styles.dropHint}>Desteklenen formatlar: JPG, PNG — Maks. 10 MB</p>
            <button
              className={styles.btnSelect}
              type="button"
              onClick={(e) => { e.stopPropagation(); fileInputRef.current.click(); }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
              Fotoğraf Seç
            </button>
          </>
        ) : (
          /* Preview state */
          <div className={styles.previewWrap} onClick={(e) => e.stopPropagation()}>
            <img src={preview} alt="Önizleme" className={styles.previewImg} />
            <p className={styles.previewMeta}>
              {file.name}  •  {(file.size / 1024).toFixed(0)} KB
            </p>
            <button className={styles.btnClear} type="button" onClick={clearFile}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="3" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
              Kaldır
            </button>
          </div>
        )}
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        accept="image/jpeg,image/png"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files[0])}
      />

      {/* Error message */}
      {error && (
        <div className={styles.errorBox}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {error}
        </div>
      )}

      {/* Analyze button */}
      <button
        className={styles.btnAnalyze}
        type="button"
        disabled={loading}
        onClick={handleAnalyze}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        {loading ? 'Analiz ediliyor...' : 'Analizi Başlat'}
      </button>
    </div>
  );
}
