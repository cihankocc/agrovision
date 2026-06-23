import { useState } from 'react';
import { API_FERTILIZER } from '../config';
import styles from './FertilizerForm.module.css';

const CROP_OPTIONS = [
  'Barley', 'Cotton', 'Ground Nuts', 'Maize', 'Millets', 
  'Oil seeds', 'Paddy', 'Pulses', 'Sugarcane', 'Tobacco', 'Wheat'
];

const SOIL_OPTIONS = [
  'Black', 'Clayey', 'Loamy', 'Red', 'Sandy'
];

export default function FertilizerForm() {
  const [formData, setFormData] = useState({
    temperature: '',
    humidity: '',
    moisture: '',
    soil_type: 'Loamy',
    crop_type: 'Wheat',
    nitrogen: '',
    potassium: '',
    phosphorous: ''
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    // Convert strings to numbers for numerical fields
    const payload = {
      temperature: parseFloat(formData.temperature),
      humidity: parseFloat(formData.humidity),
      moisture: parseFloat(formData.moisture),
      soil_type: formData.soil_type,
      crop_type: formData.crop_type,
      nitrogen: parseInt(formData.nitrogen, 10),
      potassium: parseInt(formData.potassium, 10),
      phosphorous: parseInt(formData.phosphorous, 10),
    };

    try {
      const res = await fetch(API_FERTILIZER, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) throw new Error('API Hatası');
      const data = await res.json();
      setResult(data.recommended_fertilizer);
    } catch (err) {
      setError('Gübre önerisi alınırken bir hata oluştu. Lütfen bağlantıyı kontrol edin.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <h2 className={styles.heading}>
        <span className={styles.icon}>🌱</span>
        Gübre Öneri Sistemi
      </h2>
      <p className={styles.subtitle}>
        Toprak analizi ve ortam değerlerini girerek en uygun gübreyi saniyeler içinde öğrenin.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.grid}>
          {/* NPK Section */}
          <div className={styles.inputGroup}>
            <label>Azot (N)</label>
            <input type="number" name="nitrogen" value={formData.nitrogen} onChange={handleChange} required placeholder="Örn: 30" />
          </div>
          <div className={styles.inputGroup}>
            <label>Fosfor (P)</label>
            <input type="number" name="phosphorous" value={formData.phosphorous} onChange={handleChange} required placeholder="Örn: 50" />
          </div>
          <div className={styles.inputGroup}>
            <label>Potasyum (K)</label>
            <input type="number" name="potassium" value={formData.potassium} onChange={handleChange} required placeholder="Örn: 40" />
          </div>

          {/* Environment Section */}
          <div className={styles.inputGroup}>
            <label>Sıcaklık (°C)</label>
            <input type="number" step="0.1" name="temperature" value={formData.temperature} onChange={handleChange} required placeholder="Örn: 26.5" />
          </div>
          <div className={styles.inputGroup}>
            <label>Nem (%)</label>
            <input type="number" step="0.1" name="humidity" value={formData.humidity} onChange={handleChange} required placeholder="Örn: 52.0" />
          </div>
          <div className={styles.inputGroup}>
            <label>Toprak Nemi</label>
            <input type="number" step="0.1" name="moisture" value={formData.moisture} onChange={handleChange} required placeholder="Örn: 38" />
          </div>

          {/* Categorical Section */}
          <div className={styles.inputGroup}>
            <label>Toprak Tipi</label>
            <select name="soil_type" value={formData.soil_type} onChange={handleChange}>
              {SOIL_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
          <div className={styles.inputGroup}>
            <label>Mahsul Tipi</label>
            <select name="crop_type" value={formData.crop_type} onChange={handleChange}>
              {CROP_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <button type="submit" className={styles.submitBtn} disabled={loading}>
          {loading ? 'Hesaplanıyor...' : 'Gübre Önerisi Al'}
        </button>
      </form>

      {result && (
        <div className={styles.resultBox}>
          <div className={styles.resultTitle}>Önerilen Gübre</div>
          <div className={styles.resultValue}>{result}</div>
        </div>
      )}
    </div>
  );
}
