// config.js
const isLocal = window.location.hostname === "localhost"; // เช็คว่ารันบนเครื่องตัวเองอยู่หรือเปล่า
const BASE_URL = isLocal 
  ? "http://localhost:8000" 
  : "https://panss270-findfont-project.hf.space";

export const getApiUrl = (path) => `${BASE_URL}${path}`;