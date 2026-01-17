// iOS Swift: Push Notification Token Registration
// 
// This example demonstrates how to request notification permissions,
// obtain an APNS device token, and register it with the backend.
//
// Usage:
// 1. Add to your iOS app (e.g., in AppDelegate or a dedicated PushManager class)
// 2. Call requestPermission() during app initialization
// 3. Implement the delegate methods in AppDelegate

import UserNotifications
import UIKit

class PushManager {
    private let backendURL = "http://localhost:8080" // Change to production URL
    private let userID = "00000000-0000-0000-0000-000000000001" // Get from auth
    
    // MARK: - Permission Request
    
    /// Request notification permission from the user
    func requestPermission() {
        UNUserNotificationCenter.current().requestAuthorization(
            options: [.alert, .sound, .badge]
        ) { [weak self] granted, error in
            guard let self = self else { return }
            
            if let error = error {
                print("Permission request error: \(error.localizedDescription)")
                return
            }
            
            if granted {
                print("Notification permission granted")
                DispatchQueue.main.async {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            } else {
                print("Notification permission denied")
            }
        }
    }
    
    // MARK: - Token Registration
    
    /// Called by AppDelegate when token is received
    func didRegisterForRemoteNotifications(deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        print("APNS device token: \(token)")
        
        registerTokenWithBackend(token: token, platform: "apns")
    }
    
    /// Called by AppDelegate when registration fails
    func didFailToRegisterForRemoteNotifications(error: Error) {
        print("Failed to register for remote notifications: \(error.localizedDescription)")
    }
    
    // MARK: - Backend Integration
    
    /// Register the APNS token with the backend
    private func registerTokenWithBackend(token: String, platform: String) {
        guard let url = URL(string: "\(backendURL)/v1/notifications/subscriptions") else {
            print("Invalid backend URL")
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(userID, forHTTPHeaderField: "X-User-ID")
        
        let body: [String: Any] = [
            "endpoint": token,
            "platform": platform
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        } catch {
            print("Failed to serialize request body: \(error)")
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                print("Token registration failed: \(error.localizedDescription)")
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                print("Invalid response from server")
                return
            }
            
            if httpResponse.statusCode == 200 || httpResponse.statusCode == 201 {
                print("Token registered successfully")
                
                if let data = data,
                   let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let subscriptionID = json["id"] as? String {
                    // Store subscription ID for later deletion
                    UserDefaults.standard.set(subscriptionID, forKey: "push_subscription_id")
                    print("Subscription ID: \(subscriptionID)")
                }
            } else {
                print("Token registration failed with status: \(httpResponse.statusCode)")
            }
        }.resume()
    }
    
    // MARK: - Unregistration
    
    /// Delete the push subscription from the backend
    func unregisterFromBackend() {
        guard let subscriptionID = UserDefaults.standard.string(forKey: "push_subscription_id"),
              let url = URL(string: "\(backendURL)/v1/notifications/subscriptions/\(subscriptionID)") else {
            print("No subscription to delete")
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue(userID, forHTTPHeaderField: "X-User-ID")
        
        URLSession.shared.dataTask(with: request) { _, response, error in
            if let error = error {
                print("Unregistration failed: \(error.localizedDescription)")
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                print("Invalid response from server")
                return
            }
            
            if httpResponse.statusCode == 204 {
                print("Successfully unregistered from push notifications")
                UserDefaults.standard.removeObject(forKey: "push_subscription_id")
            } else {
                print("Unregistration failed with status: \(httpResponse.statusCode)")
            }
        }.resume()
    }
}

// MARK: - AppDelegate Integration

// Add to your AppDelegate.swift:
/*
func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
) -> Bool {
    // Request notification permission
    PushManager.shared.requestPermission()
    return true
}

func application(
    _ application: UIApplication,
    didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
) {
    PushManager.shared.didRegisterForRemoteNotifications(deviceToken: deviceToken)
}

func application(
    _ application: UIApplication,
    didFailToRegisterForRemoteNotificationsWithError error: Error
) {
    PushManager.shared.didFailToRegisterForRemoteNotifications(error: error)
}
*/
