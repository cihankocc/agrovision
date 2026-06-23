import styles from './Header.module.css';

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <div className={styles.logo}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
               stroke="#86efac" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a10 10 0 0 1 10 10"/>
            <path d="M12 2C6.5 2 2 6.5 2 12"/>
            <path d="M12 22V12"/>
            <path d="M12 12c0-4 2-8 5-10"/>
            <path d="M12 12c0-4-2-8-5-10"/>
            <path d="M12 12c4 0 8-2 10-5"/>
            <path d="M12 12c-4 0-8-2-10-5"/>
          </svg>
        </div>
        <div className={styles.text}>
          <h1>AgroVision</h1>
          <p>Buğday Tarlası Yapay Zeka Analiz Sistemi</p>
        </div>
        <div className={styles.badge}>
          <span className={styles.pulseDot} />
          Aktif
        </div>
      </div>
    </header>
  );
}
