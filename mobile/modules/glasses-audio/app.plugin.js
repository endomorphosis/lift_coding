const { withDangerousMod, withPlugins } = require('@expo/config-plugins');
const path = require('path');
const fs = require('fs');

/**
 * Expo config plugin to add the GlassesAudio native module
 */
const withGlassesAudio = (config) => {
  return withDangerousMod(config, [
    'ios',
    async (config) => {
      const projectRoot = config.modRequest.projectRoot;
      const iosModulePath = path.join(projectRoot, 'modules', 'glasses-audio', 'ios');
      const podfilePath = path.join(config.modRequest.platformProjectRoot, 'Podfile');
      
      // Read Podfile
      let podfileContent = fs.readFileSync(podfilePath, 'utf8');
      
      // Add pod if not already present
      const podEntry = `  pod 'GlassesAudio', :path => '../modules/glasses-audio/ios'`;
      if (!podfileContent.includes('GlassesAudio')) {
        // Add after expo-modules line
        podfileContent = podfileContent.replace(
          /use_expo_modules!/,
          `use_expo_modules!\n${podEntry}`
        );
        fs.writeFileSync(podfilePath, podfileContent);
      }
      
      return config;
    },
  ]);
};

module.exports = withGlassesAudio;
