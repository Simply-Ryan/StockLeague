# StockLeague Mobile Implementation Plan

## Overview
This document details the comprehensive strategy to convert StockLeague from a web-only app into mobile-native apps for iOS and Android using PWA + Capacitor approach, without remaking the existing Flask backend.

---

## Executive Summary

**Approach:** Progressive Web App (PWA) + Capacitor Wrapper
- **Timeline:** 8-12 weeks
- **Effort:** Medium (no full rewrite)
- **Cost:** Minimal (open-source tools)
- **Outcome:** iOS app + Android app + Enhanced web app
- **Maintenance:** Single codebase maintained

---

## Phase 1: Progressive Web App Foundation (Weeks 1-2)

### 1.1 Add PWA Manifest
**File to create:** `static/manifest.json`
```json
{
  "name": "StockLeague",
  "short_name": "StockLeague",
  "description": "Interactive stock league gaming platform",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "theme_color": "#1a1a2e",
  "background_color": "#ffffff",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/static/images/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/static/images/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/static/images/icon-maskable.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/static/images/screenshot-540x720.png",
      "sizes": "540x720",
      "type": "image/png",
      "form_factor": "narrow"
    },
    {
      "src": "/static/images/screenshot-1280x720.png",
      "sizes": "1280x720",
      "type": "image/png",
      "form_factor": "wide"
    }
  ]
}
```

**Changes to app.py:**
- Add manifest.json link to base template
- Add meta tags for web app capability:
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#1a1a2e">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="StockLeague">
  <link rel="manifest" href="/static/manifest.json">
  <link rel="icon" type="image/png" href="/static/images/icon-192x192.png">
  <link rel="apple-touch-icon" href="/static/images/icon-192x192.png">
  ```

### 1.2 Create Service Worker
**File to create:** `static/service-worker.js`

Features:
- Cache strategy for assets (Cache-First for static files)
- Network-first for API calls
- Offline fallback page
- Push notification handling
- Background sync

```javascript
// Service worker for StockLeague PWA
const CACHE_VERSION = 'v1.0';
const CACHE_NAME = `stockleague-${CACHE_VERSION}`;

const ASSETS_TO_CACHE = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/images/icon-192x192.png',
  '/offline.html'
];

// Installation
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Activation
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // API calls: Network-first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, clone);
          });
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Static assets: Cache-first
  event.respondWith(
    caches.match(request).then((response) => {
      return response || fetch(request);
    })
  );
});

// Push notifications
self.addEventListener('push', (event) => {
  const options = {
    body: event.data?.text() || 'New notification from StockLeague',
    icon: '/static/images/icon-192x192.png',
    badge: '/static/images/badge-72x72.png',
    tag: 'stockleague-notification',
    requireInteraction: false
  };
  event.waitUntil(
    self.registration.showNotification('StockLeague', options)
  );
});
```

### 1.3 Update Flask App for PWA Support
Add to `app.py`:
```python
@app.route('/offline.html')
def offline():
    """Offline fallback page"""
    return render_template('offline.html')

@app.route('/service-worker.js')
def service_worker():
    """Serve service worker with correct MIME type"""
    response = send_file('static/service-worker.js', 
                        mimetype='application/javascript')
    response.cache_control.no_cache = True
    return response
```

### 1.4 Register Service Worker
Add to base template (likely `templates/layout.html`):
```javascript
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js')
      .then(reg => console.log('Service Worker registered'))
      .catch(err => console.log('Service Worker registration failed'));
  }

  // Install prompt
  let deferredPrompt;
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    // Show install button when appropriate
    document.getElementById('install-btn')?.style.display = 'block';
  });

  document.getElementById('install-btn')?.addEventListener('click', () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then((choiceResult) => {
        if (choiceResult.outcome === 'accepted') {
          console.log('User accepted the install prompt');
        }
        deferredPrompt = null;
      });
    }
  });
</script>
```

### 1.5 Create Offline Experience
**File to create:** `templates/offline.html`
- Display when network unavailable
- Show cached content if available
- Queue user actions for when network returns

### 1.6 Update Static Assets
**Images needed:**
- `static/images/icon-192x192.png` (192x192)
- `static/images/icon-512x512.png` (512x512)
- `static/images/icon-maskable.png` (192x192, for icon masking)
- `static/images/badge-72x72.png` (72x72)
- `static/images/screenshot-540x720.png` (narrow)
- `static/images/screenshot-1280x720.png` (wide)

---

## Phase 2: Mobile-Responsive UI Optimization (Weeks 2-3)

### 2.1 Viewport and Layout Fixes
Audit current CSS:
- Ensure all templates use `viewport` meta tag (done in Phase 1)
- Make sure no fixed-size containers break on mobile
- Test on 375px (iPhone SE), 412px (Android), 768px (iPad)

### 2.2 Touch-Friendly Interactions
- Minimum touch target size: 48x48px
- Replace hover interactions with tap-friendly alternatives
- Add haptic feedback support:

```javascript
// Haptic feedback on button clicks
function triggerHaptic() {
  if (navigator.vibrate) {
    navigator.vibrate(10); // 10ms vibration
  }
}

document.querySelectorAll('button').forEach(btn => {
  btn.addEventListener('click', triggerHaptic);
});
```

### 2.3 Responsive Grid System
- Ensure responsive breakpoints work for:
  - Mobile: 320px-480px
  - Tablet: 481px-768px
  - Desktop: 769px+

### 2.4 Mobile-First CSS Classes
Add to main stylesheet:
```css
/* Safe areas for notched devices */
@supports (padding: max(0px)) {
  body {
    padding-left: max(16px, env(safe-area-inset-left));
    padding-right: max(16px, env(safe-area-inset-right));
    padding-top: max(16px, env(safe-area-inset-top));
    padding-bottom: max(16px, env(safe-area-inset-bottom));
  }
}

/* Mobile-specific improvements */
@media (max-width: 480px) {
  .mobile-hidden { display: none; }
  .mobile-text { font-size: 14px; }
  .mobile-padding { padding: 8px; }
}
```

---

## Phase 3: Capacitor Setup (Weeks 4-6)

### 3.1 Initialize Capacitor Project
```bash
cd /workspaces/StockLeague
npm init -y
npm install @capacitor/core @capacitor/cli
npx cap init StockLeague com.stockleague.app
```

### 3.2 Project Structure After Capacitor Init
```
StockLeague/
├── capacitor.config.json
├── android/               (auto-generated)
│   ├── app/
│   ├── build.gradle
│   └── settings.gradle
├── ios/                   (auto-generated)
│   ├── App/
│   ├── Podfile
│   └── Pods/
├── web/                   (symlink to static assets)
└── package.json
```

### 3.3 Configure Capacitor
**File:** `capacitor.config.json`
```json
{
  "appId": "com.stockleague.app",
  "appName": "StockLeague",
  "webDir": "static",
  "bundledWebRuntime": false,
  "plugins": {
    "SplashScreen": {
      "launchShowDuration": 3000,
      "launchAutoHide": true,
      "backgroundColor": "#1a1a2e"
    },
    "PushNotifications": {
      "presentationOptions": ["badge", "sound", "alert"]
    }
  },
  "server": {
    "url": "http://localhost:5000",
    "cleartext": true
  }
}
```

### 3.4 Add Platform Support
```bash
npx cap add ios
npx cap add android
npx cap sync
```

### 3.5 Configure Build Tools

**Install requirements:**
```bash
# macOS/iOS development
# Requires Xcode (installed separately)
xcode-select --install

# Android development
# Download Android Studio and SDK
# Set ANDROID_HOME environment variable
export ANDROID_HOME=$HOME/Library/Android/sdk
```

### 3.6 Flask Backend Adjustments for Capacitor

**Update app.py:**
```python
# Add CORS support for Capacitor apps
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost", "capacitor://localhost", "ionic://localhost"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Add endpoint to get app config
@app.route('/api/config', methods=['GET'])
def get_app_config():
    """Return app configuration for mobile clients"""
    return jsonify({
        'version': '1.0.0',
        'features': {
            'notifications': True,
            'offline': True,
            'camera': True
        }
    })
```

---

## Phase 4: Native Features Integration (Weeks 6-8)

### 4.1 Push Notifications
**Install plugin:**
```bash
npm install @capacitor/push-notifications
npx cap sync
```

**Integration in app.py:**
```python
from firebase_admin import messaging

@app.route('/api/notifications/subscribe', methods=['POST'])
def subscribe_notifications():
    """Handle push notification subscription"""
    token = request.json.get('token')
    user_id = session.get('user_id')
    
    # Store token in database for later use
    db.update_notification_token(user_id, token)
    
    return jsonify({'status': 'subscribed'})

def send_league_notification(user_id, title, message):
    """Send push notification to user"""
    token = db.get_notification_token(user_id)
    if token:
        message = messaging.Message(
            notification=messaging.Notification(title, message),
            token=token
        )
        messaging.send(message)
```

**Frontend JavaScript:**
```javascript
import { PushNotifications } from '@capacitor/push-notifications';

async function setupNotifications() {
  const permStatus = await PushNotifications.checkPermissions();
  
  if (permStatus.receive === 'prompt') {
    await PushNotifications.requestPermissions();
  }
  
  if (permStatus.receive !== 'denied') {
    await PushNotifications.register();
  }
  
  PushNotifications.addListener('registration', async (token) => {
    // Send token to backend
    await fetch('/api/notifications/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token.value })
    });
  });
}
```

### 4.2 Camera Access
**Install plugin:**
```bash
npm install @capacitor/camera
npx cap sync
```

**Flask endpoint for profile photos:**
```python
@app.route('/api/profile/upload-photo', methods=['POST'])
def upload_profile_photo():
    """Handle profile photo upload from mobile camera"""
    user_id = session.get('user_id')
    file = request.files.get('photo')
    
    if file:
        filename = f"profile_{user_id}.png"
        file.save(f"static/uploads/{filename}")
        db.update_user_photo(user_id, filename)
        return jsonify({'status': 'success', 'url': f"/static/uploads/{filename}"})
    
    return jsonify({'status': 'error'}), 400
```

### 4.3 Geolocation (Optional - for league tournaments)
**Install plugin:**
```bash
npm install @capacitor/geolocation
npx cap sync
```

### 4.4 Storage API
```bash
npm install @capacitor/storage
npx cap sync
```

**Usage for offline caching:**
```javascript
import { Storage } from '@capacitor/storage';

// Cache portfolio data
async function cachePortfolio(data) {
  await Storage.set({
    key: 'user_portfolio',
    value: JSON.stringify(data)
  });
}

// Retrieve cached data
async function getCachedPortfolio() {
  const { value } = await Storage.get({ key: 'user_portfolio' });
  return value ? JSON.parse(value) : null;
}
```

---

## Phase 5: Testing (Weeks 8-10)

### 5.1 Web Testing
- Test PWA in Chrome DevTools
- Test manifest and service worker
- Test offline functionality
- Test on different viewport sizes

### 5.2 iOS Testing
**Build and run:**
```bash
npx cap open ios
# Xcode opens - select simulator and run
```

**Checklist:**
- App launches without errors
- Navigation works
- Touch interactions responsive
- Notifications work
- Camera/photos accessible
- Offline features work

### 5.3 Android Testing
**Build and run:**
```bash
npx cap open android
# Android Studio opens - select emulator and run
```

**Additional checks for Android:**
- Material Design compliance
- Back button behavior
- System permissions dialogs
- Hardware acceleration enabled

### 5.4 Performance Testing
- Lighthouse audit (target: 90+ score)
- Network throttling tests
- Battery usage monitoring
- Memory profiling

---

## Phase 6: App Store Deployment (Weeks 10-12)

### 6.1 iOS App Store
**Requirements:**
- Apple Developer account ($99/year)
- Code signing certificate
- App Store Connect setup

**Steps:**
```bash
# Build for production
npx cap build ios --release

# In Xcode:
# - Set provisioning profile
# - Increment build number
# - Archive app
# - Upload to App Store Connect
```

**Metadata:**
- App name, description, keywords
- Screenshots (6 required)
- Category: Finance
- Supported devices: iPad + iPhone
- Minimum iOS version: 14.0

### 6.2 Google Play Store
**Requirements:**
- Google Play Developer account ($25 one-time)
- Signed APK/AAB file
- App signing setup

**Steps:**
```bash
# Generate keystore
keytool -genkey -v -keystore stockleague.keystore -keyalg RSA -keysize 2048 -validity 10000

# Build for production
npx cap build android --release

# Sign APK
jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
  -keystore stockleague.keystore app-release-unsigned.apk my-key

# Align APK
zipalign -v 4 app-release-unsigned.apk app-release-signed.apk
```

**Metadata:**
- App name, short description, full description
- Screenshots (minimum 2-8 per language)
- Category: Finance
- Content rating
- Supported Android versions: 6.0+

---

## Architecture Changes Summary

### Backend (Minimal changes)
1. Add CORS support
2. Add `/api/config` endpoint
3. Implement notification backend
4. Add file upload endpoints
5. No database schema changes needed

### Frontend
1. Add PWA manifest
2. Create service worker
3. Register service worker
4. Add install UI
5. Improve responsive design
6. Integrate Capacitor plugins

### New Infrastructure
1. Firebase Cloud Messaging (for push notifications)
2. App signing certificates (iOS)
3. Keystore file (Android)
4. App Store Connect account
5. Google Play Console account

---

## File Checklist

### To Create
- [ ] `static/manifest.json`
- [ ] `static/service-worker.js`
- [ ] `templates/offline.html`
- [ ] `capacitor.config.json`
- [ ] `package.json` (initialized)
- [ ] Icon assets (5 files)

### To Modify
- [ ] `app.py` - Add PWA routes, CORS, API endpoints
- [ ] `templates/layout.html` - Add meta tags, service worker registration
- [ ] Main CSS file - Add responsive rules
- [ ] Main JS file - Add touch interactions

### Auto-Generated by Capacitor
- [ ] `android/` directory
- [ ] `ios/` directory
- [ ] Capacitor configuration files

---

## Dependency Updates

### Add to `requirements.txt` (Python)
```
flask-cors==4.0.0
firebase-admin==6.2.0  # For push notifications
```

### Add to `package.json` (Node.js)
```json
{
  "@capacitor/core": "^5.0.0",
  "@capacitor/cli": "^5.0.0",
  "@capacitor/ios": "^5.0.0",
  "@capacitor/android": "^5.0.0",
  "@capacitor/push-notifications": "^5.0.0",
  "@capacitor/camera": "^5.0.0",
  "@capacitor/storage": "^5.0.0",
  "@capacitor/geolocation": "^5.0.0"
}
```

---

## Timeline Gantt Chart

```
Week 1-2:   PWA Foundation [████████]
Week 2-3:   Mobile UI Optimization [████████]
Week 4-6:   Capacitor Setup [██████████████]
Week 6-8:   Native Features [██████████████]
Week 8-10:  Testing [██████████████]
Week 10-12: App Store Deployment [██████████████]
```

---

## Budget & Resources

### Tools & Services
| Item | Cost | Notes |
|------|------|-------|
| Apple Developer Account | $99/year | Required for iOS |
| Google Play Developer Account | $25 (one-time) | Required for Android |
| Firebase (free tier) | $0 | Push notifications |
| Xcode | Free | macOS only |
| Android Studio | Free | Cross-platform |
| **Total First Year** | **$124** | One-time investment |

### Team Requirements
- 1 Full-stack developer (primary)
- 1 QA/tester (part-time for testing phases)
- Access to Mac for iOS builds (could be cloud VM)

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| iOS app rejection | Medium | High | Follow Apple guidelines early, test thoroughly |
| Android permission issues | Low | Medium | Test on multiple devices, use Android docs |
| Performance on older phones | Medium | Medium | Optimize assets, lazy load features |
| Push notification failures | Low | Medium | Set up fallback notifications |
| Database migration errors | Low | High | Create backup, test migrations locally first |

---

## Success Criteria

- [ ] PWA installable on web browsers
- [ ] iOS app approved and live on App Store
- [ ] Android app approved and live on Google Play
- [ ] All features work on mobile (portfolio, leagues, trading)
- [ ] Lighthouse score ≥ 90
- [ ] Load time < 3 seconds on 4G
- [ ] Zero critical crashes in first month
- [ ] 95%+ test coverage for critical paths

---

## Post-Launch Support

### Maintenance Plan
- Monthly security updates
- Quarterly feature releases
- Beta testing program (TestFlight for iOS, Google Play Beta for Android)
- User feedback collection
- Performance monitoring

### Version Strategy
```
Web: Always latest (auto-update via browser)
iOS: Annual major version (minimum iOS 14)
Android: Annual major version (minimum Android 6.0)
```

---

## References & Documentation

- [PWA Documentation](https://web.dev/progressive-web-apps/)
- [Capacitor Official Docs](https://capacitorjs.com/)
- [iOS App Store Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Google Play Policies](https://play.google.com/about/developer-content-policy/)
- [Flask CORS Documentation](https://flask-cors.readthedocs.io/)
- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)

---

## Next Steps

1. **Immediate (Week 1):** Review this plan with team, adjust timeline
2. **Week 1 Start:** Create PWA foundation files
3. **Week 2 Start:** Test PWA on multiple devices
4. **Week 4 Start:** Initialize Capacitor after PWA validation
5. **Week 6 Start:** Build first beta version
6. **Week 10 Start:** Begin app store submission process

