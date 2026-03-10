jest.mock('expo-file-system', () => ({
  EncodingType: { Base64: 'base64' },
  readAsStringAsync: jest.fn(),
}));

jest.mock('../../api/client', () => ({
  uploadDevMedia: jest.fn(),
}));

const FileSystem = require('expo-file-system');
const { uploadDevMedia } = require('../../api/client');
const {
  inferWearablesMediaFormat,
  inferWearablesMediaKind,
  normalizeWearablesAssetUri,
  uploadWearablesDatAsset,
} = require('../metaWearablesDatMedia');

describe('metaWearablesDatMedia', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('normalizes local filesystem asset URIs', () => {
    expect(normalizeWearablesAssetUri('/tmp/capture.jpg')).toBe('file:///tmp/capture.jpg');
    expect(normalizeWearablesAssetUri('file:///tmp/capture.jpg')).toBe('file:///tmp/capture.jpg');
    expect(normalizeWearablesAssetUri(null)).toBeNull();
  });

  test('infers image and video media metadata from DAT results', () => {
    expect(
      inferWearablesMediaKind({
        action: 'capture_photo',
        assetUri: '/tmp/capture.jpeg',
      })
    ).toBe('image');
    expect(
      inferWearablesMediaFormat({
        action: 'capture_photo',
        assetUri: '/tmp/capture.jpeg',
      })
    ).toBe('jpeg');

    expect(
      inferWearablesMediaKind({
        action: 'stop_video_stream',
        mimeType: 'video/quicktime',
      })
    ).toBe('video');
    expect(
      inferWearablesMediaFormat({
        action: 'stop_video_stream',
        mimeType: 'video/quicktime',
      })
    ).toBe('mov');
  });

  test('uploads a DAT asset through the dev media endpoint', async () => {
    FileSystem.readAsStringAsync.mockResolvedValue('ZmFrZS1pbWFnZQ==');
    uploadDevMedia.mockResolvedValue({
      uri: 'file:///tmp/uploaded-image.jpg',
      bytes: 42,
      format: 'jpg',
      media_kind: 'image',
      mime_type: 'image/jpeg',
    });

    const result = await uploadWearablesDatAsset({
      action: 'capture_photo',
      assetUri: '/tmp/capture.jpg',
      mimeType: 'image/jpeg',
    });

    expect(FileSystem.readAsStringAsync).toHaveBeenCalledWith('file:///tmp/capture.jpg', {
      encoding: FileSystem.EncodingType.Base64,
    });
    expect(uploadDevMedia).toHaveBeenCalledWith('ZmFrZS1pbWFnZQ==', {
      media_kind: 'image',
      format: 'jpg',
      mime_type: 'image/jpeg',
    });
    expect(result).toMatchObject({
      uri: 'file:///tmp/uploaded-image.jpg',
      media_kind: 'image',
      format: 'jpg',
      mime_type: 'image/jpeg',
      source_asset_uri: 'file:///tmp/capture.jpg',
    });
  });

  test('returns null when DAT result has no asset URI', async () => {
    await expect(
      uploadWearablesDatAsset({
        action: 'capture_photo',
        assetUri: null,
      })
    ).resolves.toBeNull();
    expect(FileSystem.readAsStringAsync).not.toHaveBeenCalled();
    expect(uploadDevMedia).not.toHaveBeenCalled();
  });
});