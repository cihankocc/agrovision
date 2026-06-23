// API base URL
// Boş bırakılınca relative URL olur → hem localhost hem Google Cloud'da çalışır
// Dev modunda Vite proxy devreye girer (vite.config.js)
export const API_BASE = '';
export const API_PREDICT = `/api/predict`;
export const API_PREDICT_BATCH = `/api/predict/batch`;
export const API_FERTILIZER = `/api/recommend_fertilizer`;
export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
export const MAX_BATCH_FILES = 10;
