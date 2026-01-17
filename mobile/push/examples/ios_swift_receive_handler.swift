// iOS Swift: Push Notification Receive Handler with TTS Playback
//
// This example demonstrates how to handle incoming push notifications
// and play the notification message using TTS audio from the backend.
//
// Usage:
// 1. Add to your iOS app (e.g., in a dedicated NotificationHandler class)
// 2. Set up UNUserNotificationCenterDelegate in AppDelegate
// 3. Configure audio session for background playback

import UserNotifications
import AVFoundation
import UIKit

class NotificationHandler: NSObject, UNUserNotificationCenterDelegate {
    private let backendURL = "http://localhost:8080" // Change to production URL
    private let userID = "00000000-0000-0000-0000-000000000001" // Get from auth
    private var audioPlayer: AVAudioPlayer?
    
    // MARK: - Initialization
    
    override init() {
        super.init()
        setupAudioSession()
    }
    
    /// Configure audio session for playback in background
    private func setupAudioSession() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playback, mode: .spokenAudio)
            try audioSession.setActive(true)
        } catch {
            print("Failed to setup audio session: \(error)")
        }
    }
    
    // MARK: - Notification Handling
    
    /// Handle notification when app is in foreground
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        handleNotification(notification.request.content.userInfo)
        
        // Show banner and play sound
        completionHandler([.banner, .sound])
    }
    
    /// Handle notification when user taps on it
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        handleNotification(response.notification.request.content.userInfo)
        completionHandler()
    }
    
    /// Process notification data and trigger TTS playback
    private func handleNotification(_ userInfo: [AnyHashable: Any]) {
        print("Received notification: \(userInfo)")
        
        // Extract notification data
        guard let data = userInfo["data"] as? [String: Any] else {
            print("No data in notification payload")
            return
        }
        
        let notificationID = data["notification_id"] as? String
        let eventType = data["event_type"] as? String
        
        // Get message from notification body or fetch from backend
        if let message = userInfo["aps"] as? [String: Any],
           let alert = message["alert"] as? [String: Any],
           let body = alert["body"] as? String {
            speakNotification(message: body, notificationID: notificationID)
        } else if let notificationID = notificationID {
            // If no message in payload, fetch from backend
            fetchNotificationDetails(notificationID: notificationID)
        }
        
        print("Event type: \(eventType ?? "unknown")")
    }
    
    // MARK: - Backend Integration
    
    /// Fetch notification details from backend if not in payload
    private func fetchNotificationDetails(notificationID: String) {
        guard let url = URL(string: "\(backendURL)/v1/notifications") else {
            print("Invalid backend URL")
            return
        }
        
        var request = URLRequest(url: url)
        request.setValue(userID, forHTTPHeaderField: "X-User-ID")
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let self = self else { return }
            
            if let error = error {
                print("Failed to fetch notification: \(error.localizedDescription)")
                return
            }
            
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let notifications = json["notifications"] as? [[String: Any]] else {
                print("Invalid response format")
                return
            }
            
            // Find the notification by ID
            if let notification = notifications.first(where: { ($0["id"] as? String) == notificationID }),
               let message = notification["message"] as? String {
                self.speakNotification(message: message, notificationID: notificationID)
            }
        }.resume()
    }
    
    /// Generate TTS audio and play it
    private func speakNotification(message: String, notificationID: String?) {
        print("Speaking notification: \(message)")
        
        fetchTTS(text: message) { [weak self] audioData in
            guard let self = self, let audioData = audioData else {
                print("Failed to fetch TTS audio")
                return
            }
            
            self.playAudio(data: audioData)
        }
    }
    
    /// Fetch TTS audio from backend
    private func fetchTTS(text: String, completion: @escaping (Data?) -> Void) {
        guard let url = URL(string: "\(backendURL)/v1/tts") else {
            print("Invalid backend URL")
            completion(nil)
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(userID, forHTTPHeaderField: "X-User-ID")
        
        let body: [String: Any] = [
            "text": text,
            "format": "mp3",
            "voice": "default"
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        } catch {
            print("Failed to serialize TTS request: \(error)")
            completion(nil)
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                print("TTS request failed: \(error.localizedDescription)")
                completion(nil)
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200,
                  let data = data else {
                print("Invalid TTS response")
                completion(nil)
                return
            }
            
            print("TTS audio fetched successfully (\(data.count) bytes)")
            completion(data)
        }.resume()
    }
    
    /// Play audio data using AVAudioPlayer
    private func playAudio(data: Data) {
        do {
            audioPlayer = try AVAudioPlayer(data: data)
            audioPlayer?.prepareToPlay()
            audioPlayer?.play()
            print("Playing TTS audio")
        } catch {
            print("Failed to play audio: \(error)")
        }
    }
}

// MARK: - AppDelegate Integration

// Add to your AppDelegate.swift:
/*
let notificationHandler = NotificationHandler()

func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
) -> Bool {
    // Set notification delegate
    UNUserNotificationCenter.current().delegate = notificationHandler
    return true
}
*/

// MARK: - Info.plist Configuration

// Add to Info.plist:
/*
<key>UIBackgroundModes</key>
<array>
    <string>remote-notification</string>
    <string>audio</string>
</array>
*/
