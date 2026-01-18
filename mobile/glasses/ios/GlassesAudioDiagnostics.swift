import UIKit
import AVFoundation

public final class GlassesAudioDiagnosticsViewController: UIViewController {
    private let monitor = AudioRouteMonitor()
    private let recorder = GlassesRecorder()
    private let player = GlassesPlayer()
    
    private var lastRecordingURL: URL?

    private let routeLabel: UILabel = {
        let label = UILabel()
        label.numberOfLines = 0
        label.font = UIFont.monospacedSystemFont(ofSize: 12, weight: .regular)
        label.textColor = .label
        return label
    }()
    
    private let statusLabel: UILabel = {
        let label = UILabel()
        label.numberOfLines = 0
        label.font = UIFont.systemFont(ofSize: 14, weight: .medium)
        label.textColor = .label
        return label
    }()
    
    private let recordButton: UIButton = {
        let button = UIButton(type: .system)
        button.setTitle("🎤 Start Recording", for: .normal)
        button.titleLabel?.font = UIFont.systemFont(ofSize: 16, weight: .semibold)
        button.backgroundColor = .systemBlue
        button.setTitleColor(.white, for: .normal)
        button.layer.cornerRadius = 8
        button.contentEdgeInsets = UIEdgeInsets(top: 12, left: 20, bottom: 12, right: 20)
        return button
    }()
    
    private let playButton: UIButton = {
        let button = UIButton(type: .system)
        button.setTitle("▶️ Play Last Recording", for: .normal)
        button.titleLabel?.font = UIFont.systemFont(ofSize: 16, weight: .semibold)
        button.backgroundColor = .systemGreen
        button.setTitleColor(.white, for: .normal)
        button.layer.cornerRadius = 8
        button.contentEdgeInsets = UIEdgeInsets(top: 12, left: 20, bottom: 12, right: 20)
        button.isEnabled = false
        return button
    }()
    
    private let recordingDurationLabel: UILabel = {
        let label = UILabel()
        label.font = UIFont.monospacedSystemFont(ofSize: 14, weight: .regular)
        label.textColor = .secondaryLabel
        label.text = "Duration: 0.0s"
        label.isHidden = true
        return label
    }()
    
    private let scrollView: UIScrollView = {
        let scrollView = UIScrollView()
        scrollView.alwaysBounceVertical = true
        return scrollView
    }()
    
    private let contentStackView: UIStackView = {
        let stackView = UIStackView()
        stackView.axis = .vertical
        stackView.spacing = 20
        stackView.alignment = .fill
        return stackView
    }()
    
    private var recordingTimer: Timer?

    public override func viewDidLoad() {
        super.viewDidLoad()
        title = "Audio Diagnostics"
        view.backgroundColor = .systemBackground

        setupUI()
        setupMonitor()
        requestPermissions()
    }
    
    public override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        
        // Clean up
        if recorder.isCurrentlyRecording() {
            recorder.stopRecording()
        }
        if player.isCurrentlyPlaying() {
            player.stop()
        }
    }

    deinit {
        monitor.stop()
        recordingTimer?.invalidate()
    }
    
    private func setupUI() {
        // Setup scroll view
        scrollView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(scrollView)
        
        // Setup content stack view
        contentStackView.translatesAutoresizingMaskIntoConstraints = false
        scrollView.addSubview(contentStackView)
        
        // Create sections
        let routeSection = createSection(title: "📡 Audio Route", content: routeLabel)
        let statusSection = createSection(title: "🔍 Status", content: statusLabel)
        let recordSection = createSection(title: "🎤 Recording", content: recordButton)
        let durationSection = createSection(title: "", content: recordingDurationLabel)
        let playbackSection = createSection(title: "🔊 Playback", content: playButton)
        
        contentStackView.addArrangedSubview(routeSection)
        contentStackView.addArrangedSubview(statusSection)
        contentStackView.addArrangedSubview(recordSection)
        contentStackView.addArrangedSubview(durationSection)
        contentStackView.addArrangedSubview(playbackSection)
        
        // Button actions
        recordButton.addTarget(self, action: #selector(recordButtonTapped), for: .touchUpInside)
        playButton.addTarget(self, action: #selector(playButtonTapped), for: .touchUpInside)
        
        // Layout constraints
        NSLayoutConstraint.activate([
            scrollView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            scrollView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            scrollView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            scrollView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            
            contentStackView.topAnchor.constraint(equalTo: scrollView.topAnchor, constant: 16),
            contentStackView.leadingAnchor.constraint(equalTo: scrollView.leadingAnchor, constant: 16),
            contentStackView.trailingAnchor.constraint(equalTo: scrollView.trailingAnchor, constant: -16),
            contentStackView.bottomAnchor.constraint(equalTo: scrollView.bottomAnchor, constant: -16),
            contentStackView.widthAnchor.constraint(equalTo: scrollView.widthAnchor, constant: -32)
        ])
    }
    
    private func createSection(title: String, content: UIView) -> UIView {
        let container = UIView()
        container.backgroundColor = .secondarySystemBackground
        container.layer.cornerRadius = 10
        
        let stackView = UIStackView()
        stackView.axis = .vertical
        stackView.spacing = 8
        stackView.translatesAutoresizingMaskIntoConstraints = false
        
        if !title.isEmpty {
            let titleLabel = UILabel()
            titleLabel.text = title
            titleLabel.font = UIFont.systemFont(ofSize: 16, weight: .bold)
            titleLabel.textColor = .label
            stackView.addArrangedSubview(titleLabel)
        }
        
        stackView.addArrangedSubview(content)
        container.addSubview(stackView)
        
        NSLayoutConstraint.activate([
            stackView.topAnchor.constraint(equalTo: container.topAnchor, constant: 12),
            stackView.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 12),
            stackView.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -12),
            stackView.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -12)
        ])
        
        return container
    }
    
    private func setupMonitor() {
        monitor.start { [weak self] summary in
            DispatchQueue.main.async {
                self?.routeLabel.text = summary
                self?.updateStatus()
            }
        }
    }
    
    private func requestPermissions() {
        AVAudioSession.sharedInstance().requestRecordPermission { [weak self] granted in
            DispatchQueue.main.async {
                if granted {
                    self?.updateStatus()
                } else {
                    self?.showAlert(title: "Permission Required", message: "Microphone access is required for audio recording.")
                }
            }
        }
    }
    
    private func updateStatus() {
        let isBluetoothConnected = monitor.isBluetoothConnected()
        let deviceName = monitor.getBluetoothDeviceName()
        
        var status = ""
        if isBluetoothConnected {
            status = "✓ Bluetooth Connected"
            if let deviceName = deviceName {
                status += "\nDevice: \(deviceName)"
            }
        } else {
            status = "⚠️ No Bluetooth Device\nUsing phone mic/speaker"
        }
        
        statusLabel.text = status
    }
    
    @objc private func recordButtonTapped() {
        if recorder.isCurrentlyRecording() {
            stopRecording()
        } else {
            startRecording()
        }
    }
    
    private func startRecording() {
        // Create output file URL
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let diagnosticsPath = documentsPath.appendingPathComponent("audio_diagnostics")
        
        do {
            try FileManager.default.createDirectory(at: diagnosticsPath, withIntermediateDirectories: true)
        } catch {
            showAlert(title: "Error", message: "Failed to create diagnostics directory: \(error.localizedDescription)")
            return
        }
        
        let timestamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let fileName = "glasses_test_\(timestamp).wav"
        let fileURL = diagnosticsPath.appendingPathComponent(fileName)
        
        do {
            try recorder.startRecording(outputURL: fileURL, duration: 10.0) { [weak self] result in
                DispatchQueue.main.async {
                    self?.handleRecordingCompletion(result)
                }
            }
            
            // Update UI
            recordButton.setTitle("⏹ Stop Recording", for: .normal)
            recordButton.backgroundColor = .systemRed
            recordingDurationLabel.isHidden = false
            
            // Start timer to update duration
            recordingTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
                guard let self = self, let duration = self.recorder.getRecordingDuration() else { return }
                self.recordingDurationLabel.text = String(format: "Duration: %.1fs", duration)
            }
            
        } catch {
            showAlert(title: "Recording Error", message: error.localizedDescription)
        }
    }
    
    private func stopRecording() {
        recorder.stopRecording()
        recordingTimer?.invalidate()
        recordingTimer = nil
    }
    
    private func handleRecordingCompletion(_ result: Result<URL, Error>) {
        recordButton.setTitle("🎤 Start Recording", for: .normal)
        recordButton.backgroundColor = .systemBlue
        recordingDurationLabel.isHidden = true
        
        switch result {
        case .success(let url):
            lastRecordingURL = url
            playButton.isEnabled = true
            showAlert(title: "Recording Complete", message: "Audio saved to:\n\(url.lastPathComponent)")
            
        case .failure(let error):
            showAlert(title: "Recording Failed", message: error.localizedDescription)
        }
    }
    
    @objc private func playButtonTapped() {
        guard let fileURL = lastRecordingURL else { return }
        
        if player.isCurrentlyPlaying() {
            player.stop()
            playButton.setTitle("▶️ Play Last Recording", for: .normal)
            playButton.backgroundColor = .systemGreen
        } else {
            do {
                try player.play(fileURL: fileURL) { [weak self] error in
                    DispatchQueue.main.async {
                        self?.playButton.setTitle("▶️ Play Last Recording", for: .normal)
                        self?.playButton.backgroundColor = .systemGreen
                        
                        if let error = error {
                            self?.showAlert(title: "Playback Error", message: error.localizedDescription)
                        }
                    }
                }
                
                playButton.setTitle("⏹ Stop Playback", for: .normal)
                playButton.backgroundColor = .systemOrange
                
            } catch {
                showAlert(title: "Playback Error", message: error.localizedDescription)
            }
        }
    }
    
    private func showAlert(title: String, message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default))
        present(alert, animated: true)
    }
}
