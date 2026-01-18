import UIKit

final class GlassesAudioDiagnosticsViewController: UIViewController {
    private let monitor = AudioRouteMonitor()

    private let routeLabel: UILabel = {
        let label = UILabel()
        label.numberOfLines = 0
        label.font = UIFont.monospacedSystemFont(ofSize: 12, weight: .regular)
        return label
    }()

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Audio Diagnostics"
        view.backgroundColor = .systemBackground

        routeLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(routeLabel)

        NSLayoutConstraint.activate([
            routeLabel.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 16),
            routeLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 16),
            routeLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
        ])

        monitor.start { [weak self] summary in
            DispatchQueue.main.async {
                self?.routeLabel.text = summary
            }
        }
    }

    deinit {
        monitor.stop()
    }
}
