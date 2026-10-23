// Public item ids (DATA_MODEL 2.6): "ENDR-" and 8 characters of Crockford base 32. A scanned QR
// must be exactly that; a typed id is sent as typed, because the server reads look-alikes.

const PUBLIC_ID = /^ENDR-[0-9A-HJKMNP-TV-Z]{8}$/;

export function isPublicId(text: string): boolean {
  return PUBLIC_ID.test(text);
}
