const appJson = require('./app.json');

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function applyDatDisplayModeOverride(expoConfig, mode) {
  if (mode !== 'enabled' && mode !== 'disabled') {
    return expoConfig;
  }

  const enableDisplay = mode === 'enabled';
  const plugins = Array.isArray(expoConfig.plugins) ? expoConfig.plugins : [];

  expoConfig.plugins = plugins.map((pluginEntry) => {
    const pluginPath = Array.isArray(pluginEntry) ? String(pluginEntry[0]) : String(pluginEntry);
    if (!pluginPath.includes('expo-meta-wearables-dat/app.plugin.js')) {
      return pluginEntry;
    }

    const options = Array.isArray(pluginEntry) && pluginEntry[1] && typeof pluginEntry[1] === 'object'
      ? pluginEntry[1]
      : {};

    return [
      Array.isArray(pluginEntry) ? pluginEntry[0] : pluginEntry,
      {
        ...options,
        enableDisplay,
        iosDamEnabled: enableDisplay ? true : options.iosDamEnabled === true,
        androidDamEnabled: enableDisplay ? true : options.androidDamEnabled === true,
      },
    ];
  });

  return expoConfig;
}

const config = clone(appJson);
const expo = clone(config.expo || {});
const datDisplayMode = String(process.env.MWDAT_DISPLAY_MODE || '').toLowerCase();

applyDatDisplayModeOverride(expo, datDisplayMode);

module.exports = {
  ...config,
  expo,
};

