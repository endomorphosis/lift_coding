Pod::Spec.new do |s|
  s.name           = 'GlassesAudio'
  s.version        = '1.0.0'
  s.summary        = 'Native audio routing for Meta AI Glasses'
  s.description    = 'Provides AVAudioSession monitoring and native audio I/O for Bluetooth glasses'
  s.author         = ''
  s.homepage       = 'https://github.com/endomorphosis/lift_coding'
  s.platform       = :ios, '13.0'
  s.source         = { git: '' }
  s.static_framework = true

  s.dependency 'ExpoModulesCore'

  s.source_files = "**/*.{h,m,swift}"
end
