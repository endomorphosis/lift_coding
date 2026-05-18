const { withAndroidManifest, withInfoPlist } = require('expo/config-plugins');

function parseVersion(version) {
  return String(version || '')
    .split('.')
    .map((part) => Number.parseInt(part, 10) || 0);
}

function versionAtLeast(current, minimum) {
  const lhs = parseVersion(current);
  const rhs = parseVersion(minimum);
  const length = Math.max(lhs.length, rhs.length);
  for (let index = 0; index < length; index += 1) {
    const left = lhs[index] || 0;
    const right = rhs[index] || 0;
    if (left > right) return true;
    if (left < right) return false;
  }
  return true;
}

function withMetaWearablesDat(config, options = {}) {
  const enableDisplay = options.enableDisplay === true;
  const datSdkVersion = options.datSdkVersion || '0.7.0';
  const iosAnalyticsOptOut = options.iosAnalyticsOptOut !== false;
  const iosDamEnabled = options.iosDamEnabled === true || enableDisplay;
  const iosApplicationId = options.iosApplicationId || options.androidApplicationId || '';
  const androidAnalyticsOptOut = options.androidAnalyticsOptOut !== false;
  const androidApplicationId = options.androidApplicationId || '';
  const androidDamEnabled = options.androidDamEnabled === true || enableDisplay;

  if (enableDisplay && !androidApplicationId) {
    throw new Error(
      'expo-meta-wearables-dat: enableDisplay=true requires androidApplicationId (your Meta Wearables application identifier from Wearables Developer Center) for DAM setup.'
    );
  }
  if (enableDisplay && !iosApplicationId) {
    throw new Error(
      'expo-meta-wearables-dat: enableDisplay=true requires iosApplicationId (your Meta Wearables application identifier from Wearables Developer Center) for DAM setup.'
    );
  }
  if (enableDisplay && !versionAtLeast(datSdkVersion, '0.7.0')) {
    throw new Error(
      `expo-meta-wearables-dat: enableDisplay=true requires datSdkVersion >= 0.7.0 (received ${datSdkVersion}).`
    );
  }

  config = withInfoPlist(config, (configWithInfo) => {
    const currentMwdat = configWithInfo.modResults.MWDAT || {};
    const currentAppModel = currentMwdat.AppModel || {};
    configWithInfo.modResults.MWDAT = {
      ...currentMwdat,
      ApplicationId: iosApplicationId || currentMwdat.ApplicationId,
      DATSDKVersionTarget: datSdkVersion,
      AppModel: {
        ...currentAppModel,
        DAMEnabled: iosDamEnabled,
      },
      Analytics: {
        ...(currentMwdat.Analytics || {}),
        OptOut: iosAnalyticsOptOut,
      },
    };
    return configWithInfo;
  });

  config = withAndroidManifest(config, (configWithManifest) => {
    const app = configWithManifest.modResults.manifest.application?.[0];
    if (!app) {
      return configWithManifest;
    }

    const metaData = app['meta-data'] || [];
    const setMetaData = (name, value) => {
      const existing = metaData.find((entry) => entry.$['android:name'] === name);
      if (existing) {
        existing.$['android:value'] = value;
      } else {
        metaData.push({
          $: {
            'android:name': name,
            'android:value': value,
          },
        });
      }
    };

    setMetaData('com.meta.wearable.mwdat.APPLICATION_ID', androidApplicationId);
    setMetaData('com.meta.wearable.mwdat.DAM_ENABLED', androidDamEnabled ? 'true' : 'false');
    setMetaData('com.meta.wearable.mwdat.DAT_SDK_VERSION_TARGET', String(datSdkVersion));
    setMetaData(
      'com.meta.wearable.mwdat.ANALYTICS_OPT_OUT',
      androidAnalyticsOptOut ? 'true' : 'false'
    );
    app['meta-data'] = metaData;
    return configWithManifest;
  });
  return config;
}

module.exports = withMetaWearablesDat;
