import styles from './LoadingState.module.css';

export default function LoadingState() {
  return (
    <div className={styles.wrap}>
      <div className={styles.spinner} />
      <p className={styles.text}>Yapay zeka analiz ediyor...</p>
      <p className={styles.sub}>Bu işlem birkaç saniye sürebilir</p>
    </div>
  );
}
