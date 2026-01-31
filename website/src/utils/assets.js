/** Base URL for static assets (e.g. /FamilyEye/ on GitHub Pages). */
export const BASE_URL = typeof import.meta.env.BASE_URL === 'string' ? import.meta.env.BASE_URL : '/'

/** Path to an image in public/images (no leading slash). */
export function img(path) {
  const p = path.startsWith('/') ? path.slice(1) : path
  return BASE_URL + p
}
