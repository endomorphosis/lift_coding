const { withAndroidManifest, withInfoPlist } = require('expo/config-plugins');

function withMetaWearablesDat(config, options = {}) {
  const iosAnalyticsOptOut = options.iosAnalyticsOptOut !== false;
  const androidAnalyticsOptOut = options.androidAnalyticsOptOut !== false;
  const androidApplicationId = options.androidApplicationId || '';

  config = withInfoPlist(config, (configWithInfo) => {
    configWithInfo.modResults.MWDAT = {
      ...(configWithInfo.modResults.MWDAT || {}),
      Analytics: {
        ...((configWithInfo.modResults.MWDAT || {}).Analytics || {}),
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
