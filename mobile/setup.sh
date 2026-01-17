#!/bin/bash

# Quick setup script for expo-dev-client development
# This script helps prepare the mobile app for development with native modules

set -e

echo "🚀 Setting up Expo Dev Client with Native Modules"
echo ""

# Check if we're in the mobile directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Run this script from the mobile/ directory"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Check for required tools
echo ""
echo "🔍 Checking for required tools..."

if ! command -v expo &> /dev/null; then
    echo "⚠️  Expo CLI not found. Installing..."
    npm install -g expo-cli
fi

if ! command -v eas &> /dev/null; then
    echo "⚠️  EAS CLI not found. Installing..."
    npm install -g eas-cli
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo ""
echo "For local development build:"
echo "  iOS:     npx expo prebuild --platform ios && cd ios && pod install && cd .."
echo "           npx expo run:ios --device"
echo ""
echo "  Android: npx expo prebuild --platform android"
echo "           npx expo run:android --device"
echo ""
echo "For cloud build with EAS:"
echo "  1. eas init (first time only)"
echo "  2. eas build --profile development --platform [ios|android]"
echo ""
echo "For more details, see BUILD.md"
echo ""
