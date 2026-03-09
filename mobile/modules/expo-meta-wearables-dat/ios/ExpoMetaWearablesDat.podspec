Pod::Spec.new do |s|
  s.name           = 'ExpoMetaWearablesDat'
  s.version        = '1.0.0'
  s.summary        = 'Expo bridge for Meta Wearables DAT diagnostics and session control'
  s.description    = 'Provides Expo module bindings for Meta Wearables DAT configuration, diagnostics, and session lifecycle.'
  s.author         = ''
  s.homepage       = 'https://github.com/endomorphosis/lift_coding'
  s.platform       = :ios, '15.1'
  s.source         = { git: '' }
  s.static_framework = true

  s.dependency 'ExpoModulesCore'

  s.source_files = '**/*.{h,m,swift}'
end
