import { useState, useRef, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import styles from './MapPicker.module.css';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon   from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl:       markerIcon,
  shadowUrl:     markerShadow,
});

// Şanlıurfa — Türkiye'nin buğday başkenti
const SANLIURFA = [37.1591, 38.7969];

// Haritaya tıklanınca marker
function ClickHandler({ onMapClick }) {
  useMapEvents({ click(e) { onMapClick(e.latlng.lat, e.latlng.lng); } });
  return null;
}

// Dışarıdan flyTo komutunu dinleyen bileşen
function FlyController({ target }) {
  const map = useMapEvents({});
  useEffect(() => {
    if (target) map.flyTo([target.lat, target.lng], 14, { duration: 1.2 });
  }, [target, map]);
  return null;
}

export default function MapPicker({ onLocationSelect }) {
  const [marker,   setMarker]   = useState(null);
  const [flyTo,    setFlyTo]    = useState(null);   // { lat, lng } → FlyController
  const [query,    setQuery]    = useState('');
  const [results,  setResults]  = useState([]);
  const [searching, setSearching] = useState(false);
  const [showDrop,  setShowDrop]  = useState(false);
  const debounceRef = useRef(null);
  const wrapRef     = useRef(null);

  // Dışarı tıklayınca dropdown kapat
  useEffect(() => {
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setShowDrop(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Nominatim arama — 500ms debounce
  const handleQueryChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    setShowDrop(false);
    clearTimeout(debounceRef.current);
    if (val.trim().length < 3) { setResults([]); return; }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(val)}&format=json&limit=5&accept-language=tr&countrycodes=tr`;
        const res = await fetch(url, { headers: { 'Accept-Language': 'tr' } });
        const data = await res.json();
        setResults(data);
        setShowDrop(data.length > 0);
      } catch { /* sessizce geç */ }
      finally { setSearching(false); }
    }, 500);
  };

  const handleSelect = (item) => {
    const lat = parseFloat(parseFloat(item.lat).toFixed(5));
    const lng = parseFloat(parseFloat(item.lon).toFixed(5));
    const loc = { lat, lng };
    setMarker(loc);
    setFlyTo(loc);
    onLocationSelect(loc);
    // Sadece ilk parçayı (köy/ilçe adı) göster
    setQuery(item.display_name.split(',').slice(0, 2).join(',').trim());
    setShowDrop(false);
    setResults([]);
  };

  const handleMapClick = (lat, lng) => {
    const loc = { lat: parseFloat(lat.toFixed(5)), lng: parseFloat(lng.toFixed(5)) };
    setMarker(loc);
    onLocationSelect(loc);
  };

  const clearLocation = () => {
    setMarker(null);
    setFlyTo(null);
    setQuery('');
    setResults([]);
    onLocationSelect(null);
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <span className={styles.headerIcon}>🗺️</span>
        <span className={styles.headerTitle}>
          Tarla Konumu <span className={styles.optional}>(opsiyonel)</span>
        </span>
        {marker && (
          <button className={styles.clearBtn} type="button" onClick={clearLocation}>
            ✕ Konumu Temizle
          </button>
        )}
      </div>

      {/* Arama kutusu */}
      <div className={styles.searchWrap} ref={wrapRef}>
        <div className={styles.searchInputRow}>
          <svg className={styles.searchIcon} width="16" height="16" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            className={styles.searchInput}
            type="text"
            placeholder="Köy, ilçe veya tarla adı ara… (örn: Harran, Şanlıurfa)"
            value={query}
            onChange={handleQueryChange}
            onFocus={() => results.length > 0 && setShowDrop(true)}
          />
          {searching && <span className={styles.searchSpinner}>⏳</span>}
        </div>

        {/* Dropdown sonuçlar */}
        {showDrop && results.length > 0 && (
          <div className={styles.dropdown}>
            {results.map((r) => (
              <button
                key={r.place_id}
                className={styles.dropItem}
                type="button"
                onMouseDown={() => handleSelect(r)}
              >
                <span className={styles.dropItemIcon}>📍</span>
                <span className={styles.dropItemText}>{r.display_name}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Harita */}
      <div className={styles.mapWrapper}>
        <MapContainer center={SANLIURFA} zoom={10} className={styles.map} scrollWheelZoom>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClickHandler onMapClick={handleMapClick} />
          <FlyController target={flyTo} />
          {marker && (
            <Marker position={[marker.lat, marker.lng]}>
              <Popup>
                📍 Tarla Konumu<br />
                <strong>{marker.lat}°K, {marker.lng}°D</strong>
              </Popup>
            </Marker>
          )}
        </MapContainer>
      </div>

      {/* Koordinat badge */}
      {marker ? (
        <div className={styles.coordBadge}>
          <span>📍</span>
          <span>Seçilen Konum:</span>
          <strong>{marker.lat}°K, {marker.lng}°D</strong>
        </div>
      ) : (
        <p className={styles.hint}>
          Tarlanızı arama kutusundan bulun veya haritaya tıklayarak konumu işaretleyin
        </p>
      )}
    </div>
  );
}
