import * as FileSystem from 'expo-file-system';

import { uploadDevMedia } from '../api/client';

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'heic', 'webp']);
const VIDEO_EXTENSIONS = new Set(['mp4', 'mov', 'm4v', 'webm']);

export function normalizeWearablesAssetUri(uri) {
  if (!uri || typeof uri !== 'string') {
    return null;
  }
  if (uri.startsWith('file://')) {
    return uri;
  }
  if (uri.startsWith('/')) {
    return `file://${uri}`;
  }
  return uri;
}

function extensionFromUri(uri) {
  const normalized = String(uri || '').toLowerCase().split('?')[0].split('#')[0];
  const lastDotIndex = normalized.lastIndexOf('.');
  if (lastDotIndex === -1) {
    return null;
  }
  return normalized.slice(lastDotIndex + 1);
}

function mimeToFormat(mimeType, mediaKind) {
  const lower = String(mimeType || '').toLowerCase();
  if (!lower) {
    return mediaKind === 'video' ? 'mp4' : 'jpg';
  }
  const [, subtype = ''] = lower.split('/');
  switch (subtype) {
    case 'jpeg':
      return 'jpg';
    case 'quicktime':
      return 'mov';
    default:
      return subtype || (mediaKind === 'video' ? 'mp4' : 'jpg');
  }
}

export function inferWearablesMediaKind(result = {}) {
  const mimeType = String(result.mimeType || result.mime_type || '').toLowerCase();
  if (mimeType.startsWith('image/')) {
    return 'image';
  }
  if (mimeType.startsWith('video/')) {
    return 'video';
  }

  const extension = extensionFromUri(result.assetUri);
  if (extension && IMAGE_EXTENSIONS.has(extension)) {
    return 'image';
  }
  if (extension && VIDEO_EXTENSIONS.has(extension)) {
    return 'video';
  }

  const action = String(result.action || '').toLowerCase();
  if (action.includes('photo')) {
    return 'image';
  }
  if (action.includes('video')) {
    return 'video';
  }

  return 'image';
}

export function inferWearablesMediaFormat(result = {}) {
  const mediaKind = inferWearablesMediaKind(result);
  const extension = extensionFromUri(result.assetUri);
  if (extension) {
    return extension;
  }
  return mimeToFormat(result.mimeType || result.mime_type, mediaKind);
}

export async function uploadWearablesDatAsset(result = {}) {
  const assetUri = normalizeWearablesAssetUri(result.assetUri);
  if (!assetUri) {
    return null;
  }

  const mediaKind = inferWearablesMediaKind(result);
  const format = inferWearablesMediaFormat(result);
  const mimeType = result.mimeType || result.mime_type || undefined;
  const dataBase64 = await FileSystem.readAsStringAsync(assetUri, {
    encoding: FileSystem.EncodingType.Base64,
  });

  const uploaded = await uploadDevMedia(dataBase64, {
    media_kind: mediaKind,
    format,
    mime_type: mimeType,
  });

  return {
    ...uploaded,
    source_asset_uri: assetUri,
    media_kind: uploaded?.media_kind || mediaKind,
    format: uploaded?.format || format,
    mime_type: uploaded?.mime_type || mimeType || null,
  };
}